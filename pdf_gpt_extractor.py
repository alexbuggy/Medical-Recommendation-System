import os
import json
import base64
import io
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
MAX_TEXT_CHARS = 60000

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


# Cele 13 analize extractabile dintr-un buletin de laborator.
# Numele sunt IDENTICE cu feature-urile modelului neuronal.
TARGET_FIELDS = [
    "age", "sex",
    "glucose", "hba1c", "cholesterol_total", "hdl", "ldl", "triglycerides",
    "hemoglobin", "hematocrit", "wbc", "creatinine", "egfr", "bun",
    "alt", "ast", "bilirubin_total",
]


EXTRACTION_SYSTEM_PROMPT = """You are a precise medical data extractor for Romanian lab reports.
Return ONLY strict JSON, no commentary, no markdown fences.
If a value is not present in the report, return null for that field.
Never invent values. Never use reference ranges as actual values."""


def _build_user_prompt(text: str) -> str:
    return f"""Extract these lab values from the Romanian medical report below.
Return null if a value is not in the report. Use the EXACT JSON keys shown.

- age (patient age in years / varsta / ani. If only date of birth / data nasterii
       is given, compute age from it relative to the report date. Integer years.)
- sex (patient sex / sex. Return 0 for male (M / masculin / barbat),
       1 for female (F / feminin / femeie). null if not stated.)
- glucose (blood glucose / glicemie / glucoza serica / glycemia, mg/dL)
- hba1c (glycated hemoglobin / hemoglobina glicata / HbA1c, %)
- cholesterol_total (TOTAL cholesterol ONLY — NEVER HDL/LDL/VLDL — colesterol total, mg/dL)
- hdl (HDL cholesterol / colesterol HDL, mg/dL)
- ldl (LDL cholesterol / colesterol LDL, mg/dL)
- triglycerides (triglycerides / trigliceride / TG, mg/dL)
- hemoglobin (hemoglobin / hemoglobina / Hb / HGB, g/dL)
- hematocrit (hematocrit / HCT / Ht, %)
- wbc (white blood cells / leucocite / WBC / L, 10^3/uL)
- creatinine (serum creatinine / creatinina serica / CREA, mg/dL)
- egfr (estimated GFR / eGFR / RFG / rata filtrarii glomerulare, mL/min/1.73m2)
- bun (blood urea nitrogen / azot ureic / azotemie, mg/dL)
       NOTE: plain "uree"/"urea" is NOT BUN. Return null for bun unless the report
       explicitly says BUN / blood urea nitrogen / azot ureic / azotemie / nitrogen ureic.
- alt (alanine aminotransferase / ALT / TGP / GPT, U/L)
- ast (aspartate aminotransferase / AST / TGO / GOT, U/L)
- bilirubin_total (total bilirubin / bilirubina totala, mg/dL)

CRITICAL RULES:
1. Return the ACTUAL measured patient value, not reference ranges like "70-110" or "<200".
2. For cholesterol_total, ONLY the total. If HDL=50, LDL=130, Total=200, return 200 for cholesterol_total.
3. Convert decimal commas to dots (Romanian "12,5" -> 12.5).
4. Return numbers as floats, null (not 0, not "N/A") for missing values.
5. If multiple measurements of the same lab exist (different dates), return the MOST RECENT.
6. RFG = eGFR (Romanian abbreviation). Treat identically.
7. Do NOT confuse ALT/TGP with AST/TGO — they are different enzymes.

Report text:
---
{text[:MAX_TEXT_CHARS]}
---

Return ONLY a JSON object with exactly these keys:
age, sex, glucose, hba1c, cholesterol_total, hdl, ldl, triglycerides, hemoglobin,
hematocrit, wbc, creatinine, egfr, bun, alt, ast, bilirubin_total
Each value a number or null."""


def _parse_response(content: str) -> dict:
    content = (content or "").strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:]
    content = content.strip()
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"❌ GPT a returnat JSON invalid: {e}")
        print(f"   Raspuns brut: {content[:300]}")
        return {}
    out = {}
    for f in TARGET_FIELDS:
        v = data.get(f)
        if v is None:
            out[f] = np.nan
        else:
            try:
                out[f] = float(v)
            except (TypeError, ValueError):
                out[f] = np.nan
    return out


def _make_call_kwargs(use_model: str, messages: list) -> dict:
    kwargs = {
        "model": use_model,
        "messages": messages,
        "response_format": {"type": "json_object"},
    }
    if use_model.startswith("gpt-5"):
        kwargs["max_completion_tokens"] = 700
    else:
        kwargs["temperature"] = 0.0
        kwargs["max_tokens"] = 700
    return kwargs


def extract_values_with_gpt(text: str, model: str | None = None) -> dict:
    if not text or not text.strip():
        return {f: np.nan for f in TARGET_FIELDS}
    use_model = model or DEFAULT_MODEL
    print(f"🤖 Apelez {use_model} pentru extragere ({len(text)} chars)...")
    try:
        client = _get_client()
        kwargs = _make_call_kwargs(use_model, [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(text)},
        ])
        resp = client.chat.completions.create(**kwargs)
        result = _parse_response(resp.choices[0].message.content)
        found = sum(1 for v in result.values()
                    if not (isinstance(v, float) and np.isnan(v)))
        print(f" {use_model} a extras {found}/{len(TARGET_FIELDS)} valori")
        return result
    except Exception as e:
        print(f"Eroare GPT ({use_model}): {e}")
        return {}


def extract_values_from_images_with_gpt(images, model: str | None = None) -> dict:
    if not images:
        return {f: np.nan for f in TARGET_FIELDS}
    use_model = model or DEFAULT_MODEL
    print(f"🤖 Apelez {use_model} (vision) pentru imagini...")
    image_messages = []
    for img in images[:3]:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        image_messages.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"},
        })
    user_content = [
        {"type": "text", "text": _build_user_prompt("(see attached images)")},
        *image_messages,
    ]
    try:
        client = _get_client()
        kwargs = _make_call_kwargs(use_model, [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ])
        resp = client.chat.completions.create(**kwargs)
        return _parse_response(resp.choices[0].message.content)
    except Exception as e:
        print(f"❌ Eroare GPT vision ({use_model}): {e}")
        return {f: np.nan for f in TARGET_FIELDS}