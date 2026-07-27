
import os
import warnings
warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import math
import numpy as np
import pandas as pd
import joblib
from tensorflow import keras
import shap

from dotenv import load_dotenv
load_dotenv()

# ---------------------------------------------------------------------------
# DEFINITII FEATURE-URI (sincron cu modelul antrenat)
# ---------------------------------------------------------------------------

MODEL_FEATURES = [
    "age", "sex", "alt", "ast", "bilirubin_total", "bmi", "bun",
    "cholesterol_total", "creatinine", "diastolic_bp", "egfr", "glucose",
    "hba1c", "hdl", "height_cm", "hematocrit", "hemoglobin", "ldl",
    "systolic_bp", "triglycerides", "wbc", "weight_kg", "oxygen_saturation",
]

# Ce poate fi extras dintr-un buletin de analize (PDF/imagine)
PDF_EXTRACTABLE = [
    "age", "sex", "glucose", "hba1c", "cholesterol_total", "hdl", "ldl",
    "triglycerides", "hemoglobin", "hematocrit", "wbc", "creatinine",
    "egfr", "bun", "alt", "ast", "bilirubin_total",
    "systolic_bp", "diastolic_bp",
]

# Ce completeaza userul manual (masuratori fizice, nu din laborator)
USER_ONLY_FEATURES = ["height_cm", "weight_kg", "bmi", "oxygen_saturation"]

# Cele 6 clase ale modelului
VALID_SPECIALISTS = [
    "Cardiolog", "Diabetolog", "Hematolog",
    "Medicina interna", "Nefrolog", "Pneumolog",
]

# Default-uri clinice normale pentru valori lipsa (cand userul nu completeaza)
DEFAULT_VALUES = {
    "age": 50, "sex": 0, "alt": 25, "ast": 24, "bilirubin_total": 0.7,
    "bmi": 24.0, "bun": 14, "cholesterol_total": 180, "creatinine": 0.9,
    "diastolic_bp": 80, "egfr": 95, "glucose": 90, "hba1c": 5.3,
    "hdl": 55, "height_cm": 170, "hematocrit": 42, "hemoglobin": 14,
    "ldl": 100, "systolic_bp": 120, "triglycerides": 120, "wbc": 7,
    "weight_kg": 70, "oxygen_saturation": 97,
}

FEATURE_LABELS_RO = {
    "age": ("varsta", "ani"), "sex": ("sex", ""),
    "glucose": ("glicemie", "mg/dL"), "hba1c": ("HbA1c", "%"),
    "cholesterol_total": ("colesterol total", "mg/dL"),
    "hdl": ("colesterol HDL", "mg/dL"), "ldl": ("colesterol LDL", "mg/dL"),
    "triglycerides": ("trigliceride", "mg/dL"),
    "hemoglobin": ("hemoglobina", "g/dL"), "hematocrit": ("hematocrit", "%"),
    "wbc": ("leucocite", "10^3/uL"), "creatinine": ("creatinina", "mg/dL"),
    "egfr": ("eGFR", "mL/min"), "bun": ("BUN", "mg/dL"),
    "alt": ("ALT", "U/L"), "ast": ("AST", "U/L"),
    "bilirubin_total": ("bilirubina totala", "mg/dL"),
    "bmi": ("BMI", "kg/m2"),
    "systolic_bp": ("TA sistolica", "mmHg"),
    "diastolic_bp": ("TA diastolica", "mmHg"),
    "oxygen_saturation": ("saturatie oxigen", "%"),
    "height_cm": ("inaltime", "cm"), "weight_kg": ("greutate", "kg"),
}

MODEL_PATH = "models/specialist_nn.keras"
PREP_PATH = "models/nn_preprocessing.pkl"
DATASET_PATH = "data/dataset_accumulated.csv"
BACKGROUND_SIZE = 100

_MODEL = _PREP = _EXPLAINER = _FEATURE_COLS = _LABEL_ENCODER = None


def _is_nan(v):
    return v is None or (isinstance(v, float) and math.isnan(v))


def _load_all():
    global _MODEL, _PREP, _EXPLAINER, _FEATURE_COLS, _LABEL_ENCODER
    if _MODEL is not None:
        return
    if not (os.path.exists(MODEL_PATH) and os.path.exists(PREP_PATH)):
        raise FileNotFoundError(f"Lipsesc {MODEL_PATH} / {PREP_PATH}.")
    _MODEL = keras.models.load_model(MODEL_PATH)
    _PREP = joblib.load(PREP_PATH)
    _FEATURE_COLS = _PREP["feature_names"]
    _LABEL_ENCODER = _PREP["label_encoder"]
    if os.path.exists(DATASET_PATH):
        df = pd.read_csv(DATASET_PATH)
        X = df[_FEATURE_COLS].copy()
        Xs = _PREP["scaler"].transform(_PREP["imputer"].transform(X))
        idx = np.random.RandomState(42).choice(
            Xs.shape[0], min(BACKGROUND_SIZE, Xs.shape[0]), replace=False)
        background = Xs[idx]
    else:
        background = np.zeros((BACKGROUND_SIZE, len(_FEATURE_COLS)))
    _EXPLAINER = shap.DeepExplainer(_MODEL, background)


def build_full_feature_dict(extracted: dict):
    """Mapeaza valorile extrase pe cele 23 feature-uri. Returneaza (full, missing)."""
    full = {f: np.nan for f in MODEL_FEATURES}
    for f in MODEL_FEATURES:
        if not _is_nan(extracted.get(f)):
            full[f] = float(extracted[f])
    missing = [f for f in MODEL_FEATURES if _is_nan(full.get(f))]
    return full, missing


def clean_extracted(vals: dict) -> dict:
    """np.nan -> None, doar pentru campurile extractabile (pt JSON UI)."""
    out = {}
    for f in PDF_EXTRACTABLE:
        v = vals.get(f)
        out[f] = None if _is_nan(v) else float(v)
    return out


def _human_sentence(feature, raw_value, shap_value, specialist):
    label, unit = FEATURE_LABELS_RO.get(feature, (feature, ""))
    value_str = "necunoscut" if _is_nan(raw_value) else \
        f"{raw_value:g}{(' ' + unit) if unit else ''}"
    mag = abs(shap_value)
    strength = "puternic" if mag >= 0.3 else ("moderat" if mag >= 0.1 else "usor")
    direction = "a sustinut" if shap_value > 0 else "a contrazis"
    return (f"{label.capitalize()} ({value_str}) {direction} {strength} "
            f"recomandarea spre {specialist}.")


def predict_with_explanation(values: dict, top_k: int = 5) -> dict:
    """NN + SHAP. values: dict cu cele 23 feature-uri (NaN unde lipsesc)."""
    _load_all()
    # completeaza lipsa cu default ca modelul sa primeasca vector complet
    filled = {}
    used_default = []
    for f in _FEATURE_COLS:
        v = values.get(f)
        if _is_nan(v):
            filled[f] = DEFAULT_VALUES.get(f, 0)
            used_default.append(f)
        else:
            filled[f] = float(v)

    X = pd.DataFrame([filled])[_FEATURE_COLS]
    Xs = _PREP["scaler"].transform(_PREP["imputer"].transform(X))
    probs = _MODEL.predict(Xs, verbose=0)[0]
    pred_idx = int(np.argmax(probs))
    pred_name = _LABEL_ENCODER.classes_[pred_idx]

    sv = _EXPLAINER.shap_values(Xs)
    patient_shap = sv[pred_idx][0] if isinstance(sv, list) else sv[0, :, pred_idx]
    contribs = sorted(zip(_FEATURE_COLS, patient_shap),
                      key=lambda x: abs(float(x[1])), reverse=True)[:top_k]

    top_factors = []
    for feat, sh in contribs:
        sh = float(sh)
        raw = values.get(feat, np.nan)
        label, unit = FEATURE_LABELS_RO.get(feat, (feat, ""))
        top_factors.append({
            "feature": feat, "label": label,
            "value": None if _is_nan(raw) else float(raw),
            "unit": unit, "shap": round(sh, 3),
            "direction": "supports" if sh > 0 else "against",
            "sentence": _human_sentence(feat, raw, sh, pred_name),
        })

    return {
        "specialist": pred_name,
        "confidence": round(float(probs[pred_idx]), 3),
        "probabilities": {_LABEL_ENCODER.classes_[i]: round(float(probs[i]), 3)
                          for i in range(len(probs))},
        "used_default": used_default,
        "explanation": {"top_factors": top_factors},
    }


# ---------------------------------------------------------------------------
# RAPORT — online (GPT) / offline (sablon), cu toggle
# ---------------------------------------------------------------------------

def _format_values_block(values):
    lines = []
    for feat, (label, unit) in FEATURE_LABELS_RO.items():
        v = values.get(feat)
        if _is_nan(v):
            continue
        lines.append(f"- {label}: {v:g}{(' ' + unit) if unit else ''}")
    return "\n".join(lines) if lines else "(nicio valoare)"


SPECIALIST_BLURBS = {
    "Diabetolog": "Glicemia/HbA1c sugereaza o tulburare a metabolismului glucozei.",
    "Nefrolog": "Functia renala (creatinina, eGFR) indica o posibila afectare renala.",
    "Cardiolog": "Profilul lipidic/tensiunea sugereaza risc cardiovascular.",
    "Hematolog": "Hemoglobina scazuta indica o posibila anemie.",
    "Pneumolog": "Saturatia oxigenului redusa sugereaza o posibila afectare pulmonara.",
    "Medicina interna": "Valorile se incadreaza in general in limite acceptabile.",
}


def generate_report(values, specialist, top_factors=None,
                    confidence=None, use_gpt=True):
    if use_gpt:
        print(f"[RAPORT] use_gpt=True -> incerc GPT online")
        try:
            text = _report_online(values, specialist, top_factors, confidence)
            return text, True
        except Exception as e:
            import traceback
            print(f"[RAPORT] !! GPT esuat ({e!r}) -> fallback offline")
            traceback.print_exc()
    else:
        print(f"[RAPORT] use_gpt=False -> folosesc direct offline")
    text = _report_offline(values, specialist, top_factors, confidence)
    return text, False


def _report_online(values, specialist, top_factors, confidence):
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    use_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    factors_txt = "\n".join(f"- {f['sentence']}" for f in (top_factors or []))
    conf = f"\nÎncredere model: {confidence*100:.0f}%." if confidence else ""

    system_prompt = """Ești un asistent medical care oferă explicații clare și concise despre 
rezultatele analizelor medicale. Nu oferi diagnostice clinice, ci doar explicații informative.
Răspunsul tău trebuie să fie în limba română, profesional dar accesibil pacientului.
Folosești factorii SHAP pentru a explica de ce modelul a recomandat acest specialist."""

    user_prompt = f"""Pacientul are următoarele valori medicale:

{_format_values_block(values)}

Sistemul de machine learning a recomandat următorul specialist: {specialist}.{conf}

Factori care au contat cel mai mult în decizia modelului (analiză SHAP):
{factors_txt}

Te rog să generezi un raport medical de 5-8 propoziții care:
1. Prezintă valorile medicale în context (normale sau anormale, cu menționarea valorilor de referință)
2. Explică de ce a fost recomandat acest specialist, folosind factorii SHAP de mai sus
3. Identifică care valori medicale au influențat cel mai mult această decizie
4. Oferă o perspectivă clară dar empatică
5. Menționează dacă există valori care necesită atenție urgentă

Notă: Acest raport este doar informativ și nu înlocuiește consultația medicală."""

    print(f"[RAPORT-GPT] >>> Apelez {use_model} pentru raport "
          f"({len(user_prompt)} chars prompt, specialist={specialist})...")

    kwargs = {
        "model": use_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if use_model.startswith(("gpt-5", "o1", "o3", "o4")):
        kwargs["max_completion_tokens"] = 700
    else:
        kwargs["temperature"] = 0.7
        kwargs["max_tokens"] = 700

    resp = client.chat.completions.create(**kwargs)
    text = resp.choices[0].message.content

    usage = getattr(resp, "usage", None)
    if usage:
        print(f"[RAPORT-GPT] <<< OK ({use_model}): "
              f"prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, "
              f"total={usage.total_tokens} tokens, raspuns={len(text)} chars")
    else:
        print(f"[RAPORT-GPT] <<< OK ({use_model}): raspuns={len(text)} chars")

    return text


def _report_offline(values, specialist, top_factors, confidence):
    parts = []
    conf = f" (incredere model: {confidence*100:.0f}%)" if confidence else ""
    parts.append(f"Pe baza analizei valorilor, sistemul recomanda consultarea "
                 f"unui specialist {specialist}{conf}.")
    vb = _format_values_block(values)
    if vb:
        parts.append(f"\nValori analizate:\n{vb}")
    parts.append("\n" + SPECIALIST_BLURBS.get(specialist,
                 "Se recomanda evaluare medicala suplimentara."))
    if top_factors:
        parts.append("\nFactori care au contat la decizie:")
        for f in top_factors[:5]:
            parts.append(f"  - {f['sentence']}")
    parts.append("\nRaport generat automat (mod offline). NU inlocuieste "
                 "consultatia medicala profesionala.")
    return "\n".join(parts)