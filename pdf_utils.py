import os
import io
import re
import fitz
import pdfplumber
import numpy as np
from PIL import Image

import config as _config
try:
    import pytesseract as _pyt
    if _config.TESSERACT_CMD:
        _pyt.pytesseract.tesseract_cmd = _config.TESSERACT_CMD
except ImportError:
    pass

from pdf_gpt_extractor import (
    extract_values_with_gpt,
    extract_values_from_images_with_gpt,
    TARGET_FIELDS,
)

ALL_FIELDS = TARGET_FIELDS  # cele 15 analize extractabile din PDF

# Cele 23 de feature-uri ale modelului
MODEL_FEATURES = [
    "age", "sex", "alt", "ast", "bilirubin_total", "bmi", "bun",
    "cholesterol_total", "creatinine", "diastolic_bp", "egfr", "glucose",
    "hba1c", "hdl", "height_cm", "hematocrit", "hemoglobin", "ldl",
    "systolic_bp", "triglycerides", "wbc", "weight_kg", "oxygen_saturation",
]

USER_ONLY_FEATURES = [
    "height_cm", "weight_kg", "bmi",
    "systolic_bp", "diastolic_bp", "oxygen_saturation",
]

SCANNED_TEXT_THRESHOLD = 300
MIN_DIGIT_RATIO = 0.02


# Sinonime per analiza
LABEL_KEYWORDS = {
    "age": [
        "varsta", "vÃ¢rstÄƒ", "varlsta", "age", "ani impliniti",
    ],
    "sex": [
        "sex", "gen", "gender",
    ],
    "glucose": [
        "glicemie a jeun", "glicemie bazala", "fasting glucose",
        "blood glucose", "serum glucose", "glucoza serica", "glucozÄƒ sericÄƒ",
        "glicemie", "glucozÄƒ", "glucoza", "glucose", "glycemia", "glycaemia",
    ],
    "hba1c": [
        "hemoglobina glicata", "hemoglobinÄƒ glicatÄƒ", "glycated hemoglobin",
        "hemoglobina glicozilata", "hba1c", "hb a1c", "a1c",
    ],
    "cholesterol_total": [
        "colesterol total", "total cholesterol", "colesterol seric",
        "colesterol", "cholesterol", " tc ", " chol ",
    ],
    "hdl": [
        "colesterol hdl", "hdl cholesterol", "hdl-c", " hdl ",
    ],
    "ldl": [
        "colesterol ldl", "ldl cholesterol", "ldl-c", " ldl ",
    ],
    "triglycerides": [
        "trigliceride serice", "trigliceride", "triglycerides",
        "triglicerides", " tg ",
    ],
    "hemoglobin": [
        "hemoglobina sanguina", "hemoglobinÄƒ sanguinÄƒ",
        "hemoglobina", "hemoglobinÄƒ", "hemoglobin", "hgb", " hb ",
    ],
    "hematocrit": [
        "hematocrit", " hct ", " ht ",
    ],
    "wbc": [
        "leucocite", "white blood cells", "white blood cell", "wbc",
        "numar leucocite", " l ",
    ],
    "creatinine": [
        "creatinina serica", "creatininÄƒ sericÄƒ", "serum creatinine",
        "creatinina", "creatininÄƒ", "creatinine", " crea ", " cre ",
    ],
    "egfr": [
        ("regex", r"(rata|indice|estimare(?:a)?|clearance)[\s\w,.\-()]{0,50}?"
                  r"(filtr|glomerul|renal)"),
        ("regex", r"(filtr[aÄƒ]r[ie]i?|filtrare)\s+glomerular[aÄƒ]"),
        "estimated glomerular filtration rate", "estimated gfr",
        "egfr ckd-epi", "egfr ckd epi", "ckd-epi", "ckd epi",
        "raport rfg", "raport rgf",
        "egfr", "e.gfr", "e-gfr", "e gfr", "rfg", "rgf", " gfr ",
    ],
    "bun": [
        "blood urea nitrogen", "azot ureic sanguin", "azot ureic",
        "nitrogen ureic", "uree azotata", "uree azotatÄƒ", "azotemie", " bun ",
        "uree serica", "uree sericÄƒ", "serum urea", "uree", "urea",
    ],
    "alt": [
        "alanin aminotransferaza", "alanine aminotransferase",
        " alt ", " tgp ", " gpt ",
    ],
    "ast": [
        "aspartat aminotransferaza", "aspartate aminotransferase",
        " ast ", " tgo ", " got ",
    ],
    "bilirubin_total": [
        "bilirubina totala", "bilirubinÄƒ totalÄƒ", "total bilirubin",
        "bilirubina t", "bilirubin total",
    ],
}

BUN_FROM_UREE = False
UREE_TO_BUN_FACTOR = 0.467

# Limite plauzibile per analiza
NORMAL_RANGES = {
    "age":               (0, 120),
    "sex":               (0, 1),
    "glucose":           (40, 600),
    "hba1c":             (3, 20),
    "cholesterol_total": (50, 600),
    "hdl":               (10, 150),
    "ldl":               (10, 400),
    "triglycerides":     (20, 1000),
    "hemoglobin":        (3, 25),
    "hematocrit":        (10, 65),
    "wbc":               (1, 100),
    "creatinine":        (0.2, 15.0),
    "egfr":              (5, 200),
    "bun":               (2, 200),
    "alt":               (1, 2000),
    "ast":               (1, 2000),
    "bilirubin_total":   (0.1, 30),
}

# Cuvinte care INVALIDEAZA match-ul pentru acel field.
NEGATIVE_KEYWORDS = {
    "hemoglobin": ["glicat", "glicozilat", "hba1c", "hb a1c", "a1c"],
    "glucose": [],
}

DECIMAL_FIELDS = {"hemoglobin", "creatinine", "hba1c", "bilirubin_total",
                  "wbc", "hematocrit"}

NUMBER_RE = re.compile(r"(?<!\d)(\d{1,4}(?:[.,]\d{1,3})?)(?!\d)")


def detect_pdf_type(pdf_path: str):
    text = extract_text_from_pdf(pdf_path, verbose=False)
    digits = sum(1 for c in text if c.isdigit())
    ratio = digits / len(text) if text else 0
    if len(text) < SCANNED_TEXT_THRESHOLD or ratio < MIN_DIGIT_RATIO:
        return "scan", text
    return "text", text


def extract_text_from_pdf(pdf_path: str, verbose: bool = True) -> str:
    chunks = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                txt = page.extract_text(layout=True, x_tolerance=2, y_tolerance=2)
                if txt:
                    chunks.append(txt)
                try:
                    for table in page.extract_tables() or []:
                        for row in table:
                            if row:
                                chunks.append(" | ".join((c or "").strip() for c in row))
                except Exception:
                    pass
    except Exception as e:
        if verbose:
            print(f"    pdfplumber failed: {e}")
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            chunks.append(page.get_text("text"))
        doc.close()
    except Exception as e:
        if verbose:
            print(f"    PyMuPDF failed: {e}")
    text = "\n".join(chunks)
    if verbose:
        print(f" Text extras: {len(text)} caractere ({len(chunks)} bucati)")
    return text


def ocr_pdf_with_tesseract(pdf_path: str, verbose: bool = True) -> str:
    try:
        import cv2
        import pytesseract
    except ImportError:
        if verbose:
            print("  cv2/pytesseract lipsesc â€” sar peste OCR")
        return ""
    images = pdf_to_images_for_ocr(pdf_path, zoom=3)
    if verbose:
        print(f"  OCR Tesseract pe {len(images)} pagini...")
    all_text = []
    for page_idx, pil_img in enumerate(images):
        img = np.array(pil_img.convert("RGB"))[:, :, ::-1]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        candidates = []
        _, t1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        candidates.append(t1)
        t2 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY, 11, 2)
        candidates.append(t2)
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        _, t3 = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        candidates.append(t3)
        best_text, best_score = "", -1
        for cand in candidates:
            try:
                txt = pytesseract.image_to_string(cand, lang="ron+eng", config="--psm 6")
                score = sum(1 for c in txt if c.isdigit())
                if score > best_score:
                    best_score, best_text = score, txt
            except Exception:
                continue
        if verbose:
            print(f"   Pagina {page_idx + 1}: {len(best_text)} chars, {best_score} cifre")
        all_text.append(best_text)
    return "\n".join(all_text)


def _to_float(s: str) -> float:
    return float(s.replace(",", "."))


def _is_in_range(field: str, value: float) -> bool:
    lo, hi = NORMAL_RANGES[field]
    return lo <= value <= hi


def _looks_like_reference_range(line: str, num_start: int, num_end: int) -> bool:
    before = line[max(0, num_start - 3):num_start]
    after = line[num_end:num_end + 3]
    if re.search(r"[-â€“â€”]\s*$", before) or re.search(r"^\s*[-â€“â€”]", after):
        return True
    if re.search(r"[<>â‰¤â‰¥]\s*$", before):
        return True
    return False


def _find_value_for_label(lines, label_keywords, field):
    LOOKAHEAD_LINES = 5
    for keyword in label_keywords:
        if isinstance(keyword, tuple) and keyword[0] == "regex":
            pat_str = keyword[1]
            label_pattern = re.compile(pat_str, re.IGNORECASE)
            for i, line in enumerate(lines):
                if any(nk in line.lower() for nk in NEGATIVE_KEYWORDS.get(field, [])):
                    continue
                m_kw = label_pattern.search(line)
                if not m_kw:
                    continue
                kw_end = m_kw.end()
                search_window = [line[kw_end:]] + [
                    lines[i + j] if i + j < len(lines) else ""
                    for j in range(1, LOOKAHEAD_LINES + 1)]
                for window_text in search_window:
                    for m in NUMBER_RE.finditer(window_text):
                        raw = m.group(1)
                        if _looks_like_reference_range(window_text, m.start(), m.end()):
                            continue
                        try:
                            val = _to_float(raw)
                        except ValueError:
                            continue
                        if _is_in_range(field, val):
                            return val, f"[regex]{pat_str[:30]}"
            continue
        kw_clean = keyword.strip()
        kw_lower = kw_clean.lower()
        use_word_boundary = (len(kw_lower) <= 3 or keyword != keyword.strip())
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(nk in line_lower for nk in NEGATIVE_KEYWORDS.get(field, [])):
                continue
            if use_word_boundary:
                pat = re.compile(r"(?:^|[\s:.\-/(\[])" + re.escape(kw_lower)
                                  + r"(?:[\s:.\-/)\]]|$)")
                m_kw = pat.search(line_lower)
                if not m_kw:
                    continue
                kw_pos = m_kw.start() + m_kw.group(0).find(kw_lower)
                kw_end = kw_pos + len(kw_lower)
            else:
                if kw_lower not in line_lower:
                    continue
                kw_pos = line_lower.find(kw_lower)
                kw_end = kw_pos + len(kw_lower)
            search_window = [line[kw_end:]] + [
                lines[i + j] if i + j < len(lines) else ""
                for j in range(1, LOOKAHEAD_LINES + 1)]
            for window_text in search_window:
                for m in NUMBER_RE.finditer(window_text):
                    raw = m.group(1)
                    if _looks_like_reference_range(window_text, m.start(), m.end()):
                        continue
                    try:
                        val = _to_float(raw)
                    except ValueError:
                        continue
                    if _is_in_range(field, val):
                        return val, kw_clean
    return np.nan, None



def _find_age(lines):
    for line in lines:
        ll = line.lower()
        if "varsta" in ll or "vÃ¢rstÄƒ" in ll or "age" in ll:
            m = re.search(r"(\d{1,3})", ll[ll.find("varsta") if "varsta" in ll else 0:])
            if m:
                v = float(m.group(1))
                if 0 <= v <= 120:
                    return v
        m2 = re.search(r"(\d{1,3})\s*ani", ll)
        if m2:
            v = float(m2.group(1))
            if 0 <= v <= 120:
                return v
    return np.nan


def _find_sex(lines):
    for line in lines:
        ll = line.lower()
        if "sex" in ll or "gen" in ll or "gender" in ll:
            seg = ll.split("sex", 1)[-1] if "sex" in ll else ll
            if re.search(r"\b(f|feminin|femeie|female)\b", seg):
                return 1.0
            if re.search(r"\b(m|masculin|barbat|b[aÄƒ]rbat|male)\b", seg):
                return 0.0
    return np.nan


def extract_values_regex(text: str) -> dict:
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    values = {}
    matched_keywords = {}
    # age + sex au nevoie de tratament special (sex e text M/F, nu numar)
    values["age"] = _find_age(lines)
    values["sex"] = _find_sex(lines)
    for field, keywords in LABEL_KEYWORDS.items():
        if field in ("age", "sex"):
            continue
        val, matched_kw = _find_value_for_label(lines, keywords, field)
        values[field] = val
        if matched_kw:
            matched_keywords[field] = matched_kw
    # BUN: distinge intre "BUN strict" si "uree"
    if "bun" in matched_keywords:
        kw = matched_keywords["bun"].lower()
        is_uree = (kw.startswith("uree") or kw == "urea" or kw == "serum urea")
        is_strict = (kw == "bun" or "blood urea nitrogen" in kw or
                     "azot ureic" in kw or "nitrogen ureic" in kw or
                     "azotemie" in kw or "uree azot" in kw)
        if is_uree and not is_strict and not np.isnan(values["bun"]):
            uree_val = values["bun"]
            if BUN_FROM_UREE:
                values["bun"] = round(uree_val * UREE_TO_BUN_FACTOR, 2)
            else:
                values["bun"] = np.nan
    for f in ALL_FIELDS:
        values.setdefault(f, np.nan)
    return values


def pdf_to_images_for_ocr(pdf_path: str, zoom: int = 2) -> list:
    doc = fitz.open(pdf_path)
    images = []
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        images.append(Image.open(io.BytesIO(pix.tobytes("png"))))
    doc.close()
    return images


def _is_nan(v):
    return v is None or (isinstance(v, float) and np.isnan(v))


def _fill_gaps(primary: dict, secondary: dict) -> dict:
    out = dict(primary)
    for k, v in secondary.items():
        if _is_nan(out.get(k)) and not _is_nan(v):
            out[k] = v
    for f in ALL_FIELDS:
        out.setdefault(f, np.nan)
    return out


def extract_medical_values_from_pdf(pdf_path: str, use_gpt: bool = True,
                                     verbose: bool = True) -> dict:
    if verbose:
        print(f"\n{'=' * 60}")
        print(f" Procesare PDF: {os.path.basename(pdf_path)}")
        print(f"{'=' * 60}")
    pdf_type, text = detect_pdf_type(pdf_path)
    if verbose:
        print(f" Tip PDF: {pdf_type.upper()} ({len(text)} chars)")
    if pdf_type == "text":
        gpt_values = extract_values_with_gpt(text) if use_gpt else {}
        regex_values = extract_values_regex(text)
        final = _fill_gaps(gpt_values, regex_values) if gpt_values else dict(regex_values)
        source = "GPT primary + regex fill" if gpt_values else "regex only"
    else:
        if verbose:
            print(" PDF scanat â€” vision + OCR")
        gpt_values = {}
        if use_gpt:
            images = pdf_to_images_for_ocr(pdf_path)
            gpt_values = extract_values_from_images_with_gpt(images)
        ocr_text = ocr_pdf_with_tesseract(pdf_path, verbose=verbose)
        regex_values = extract_values_regex(ocr_text) if ocr_text else {}
        final = _fill_gaps(gpt_values, regex_values) if gpt_values else dict(regex_values)
        source = "GPT vision + OCR fill" if gpt_values else "OCR regex only"
    for f in ALL_FIELDS:
        final.setdefault(f, np.nan)
    if verbose:
        print(f"\n Rezultat extragere PDF ({source}):")
        for f in ALL_FIELDS:
            v = final.get(f, np.nan)
            mark = "âœ“" if not _is_nan(v) else "âœ—"
            print(f"   {mark} {f:<18} = {v}")
    return final


# Extrage valori dintr-o IMAGINE (.png/.jpg/.jpeg) â€” poza cu analizele.
# Acelasi pipeline ca PDF scanat: OCR Tesseract + GPT vision.
def extract_medical_values_from_image(img_path: str, use_gpt: bool = True,
                                       verbose: bool = True) -> dict:
    if verbose:
        print(f"\n{'=' * 60}")
        print(f"  Procesare imagine: {os.path.basename(img_path)}")
        print(f"{'=' * 60}")

    pil_img = Image.open(img_path).convert("RGB")

    # GPT vision
    gpt_values = {}
    if use_gpt:
        gpt_values = extract_values_from_images_with_gpt([pil_img])

    # OCR Tesseract pe imagine (acelasi multi-threshold ca la PDF scanat)
    ocr_text = ""
    try:
        import cv2, pytesseract
        img = np.array(pil_img)[:, :, ::-1]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        candidates = []
        _, t1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        candidates.append(t1)
        t2 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY, 11, 2)
        candidates.append(t2)
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        _, t3 = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        candidates.append(t3)
        best, best_score = "", -1
        for cand in candidates:
            try:
                txt = pytesseract.image_to_string(cand, lang="ron+eng", config="--psm 6")
                sc = sum(1 for c in txt if c.isdigit())
                if sc > best_score:
                    best_score, best = sc, txt
            except Exception:
                continue
        ocr_text = best
    except ImportError:
        if verbose:
            print("  cv2/pytesseract lipsesc â€” doar GPT vision")

    regex_values = extract_values_regex(ocr_text) if ocr_text else {}
    final = _fill_gaps(gpt_values, regex_values) if gpt_values else dict(regex_values)
    source = "GPT vision + OCR fill" if gpt_values else "OCR regex only"

    for f in ALL_FIELDS:
        final.setdefault(f, np.nan)
    if verbose:
        print(f"\n Rezultat extragere imagine ({source}):")
        for f in ALL_FIELDS:
            v = final.get(f, np.nan)
            mark = "âœ“" if not _is_nan(v) else "âœ—"
            print(f"   {mark} {f:<18} = {v}")
    return final

# Punct de intrare UNIVERSAL â€” detecteaza automat PDF vs imagine dupa extensie si cheama functia potrivita.
def extract_medical_values(file_path: str, use_gpt: bool = True,
                            verbose: bool = True) -> dict:
    ext = os.path.splitext(file_path)[1].lower()
    if ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"):
        return extract_medical_values_from_image(file_path, use_gpt, verbose)
    return extract_medical_values_from_pdf(file_path, use_gpt, verbose)


def build_full_feature_dict(pdf_values: dict) -> dict:
    """
    Construieste dict-ul COMPLET de 23 feature-uri pentru model.
    - Analizele extrase din PDF se pun la locul lor.
    - Feature-urile care nu vin din PDF (age, sex, BP, etc.) raman NaN
      => utilizatorul le completeaza in formular.
    Returneaza si lista campurilor pe care userul trebuie sa le completeze.
    """
    full = {f: np.nan for f in MODEL_FEATURES}
    for f in ALL_FIELDS:
        if f in full and not _is_nan(pdf_values.get(f)):
            full[f] = pdf_values[f]
    missing = [f for f in MODEL_FEATURES if _is_nan(full.get(f))]
    return full, missing


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    if not args:
        print("Usage: python pdf_utils.py <pdf_path> [--no-gpt]")
        sys.exit(1)
    use_gpt = "--no-gpt" not in args
    pdf_path = [a for a in args if not a.startswith("--")][0]
    vals = extract_medical_values_from_pdf(pdf_path, use_gpt=use_gpt)
    full, missing = build_full_feature_dict(vals)
    print(f"\n Feature-uri de completat de utilizator ({len(missing)}):")
    print("   " + ", ".join(missing))
