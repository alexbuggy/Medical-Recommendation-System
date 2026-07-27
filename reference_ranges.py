"""
reference_ranges.py — Extrage intervalele de referință din PDF-urile lab.
"""

import re
import numpy as np


RANGE_PATTERNS = [
    re.compile(r"(\d+(?:[.,]\d+)?)\s*[-–—…]+\s*(\d+(?:[.,]\d+)?)"),
]

UPPER_BOUND_PATTERNS = [
    re.compile(r"[<≤]\s*(\d+(?:[.,]\d+)?)"),
]

LOWER_BOUND_PATTERNS = [
    re.compile(r"[>≥]\s*(\d+(?:[.,]\d+)?)"),
]


def _to_float(s: str) -> float:
    return float(s.replace(",", "."))


def _try_match_range(window: str) -> dict:
    """Încearcă pattern-urile de range pe o fereastră dată. Întoarce dict sau None."""
    for pat in RANGE_PATTERNS:
        m = pat.search(window)
        if m:
            try:
                low = _to_float(m.group(1))
                high = _to_float(m.group(2))
                if 0 < low < high < 10000:
                    return {"low": low, "high": high, "raw": m.group(0)}
            except ValueError:
                pass
    for pat in UPPER_BOUND_PATTERNS:
        m = pat.search(window)
        if m:
            try:
                return {"low": None, "high": _to_float(m.group(1)),
                        "raw": m.group(0)}
            except ValueError:
                pass
    for pat in LOWER_BOUND_PATTERNS:
        m = pat.search(window)
        if m:
            try:
                return {"low": _to_float(m.group(1)), "high": None,
                        "raw": m.group(0)}
            except ValueError:
                pass
    return None


def _find_next_label_position(text: str, current_field: str,
                               all_label_keywords: dict) -> int:
    """Caută poziția următorului label din ALT câmp."""
    text_lower = text.lower()
    earliest = len(text)
    for field, keywords in all_label_keywords.items():
        if field == current_field:
            continue
        for kw in keywords:
            if isinstance(kw, tuple):
                continue  # sări peste pattern-uri regex
            kw = kw.strip().lower()
            if not kw or len(kw) < 3:
                continue
            pos = text_lower.find(kw)
            if 0 <= pos < earliest:
                earliest = pos
    return earliest


def find_reference_range_for_field(
    text: str,
    label_keywords: list,
    current_field: str = None,
    all_label_keywords: dict = None,
    max_search_chars: int = 200,
) -> dict:
    """Pentru un câmp dat, caută intervalul de referință în vecinătatea label-ului."""
    text_lower = text.lower()

    for keyword in label_keywords:
        # Tuple ("regex", pattern)
        if isinstance(keyword, tuple) and keyword[0] == "regex":
            try:
                pat = re.compile(keyword[1], re.IGNORECASE)
            except re.error:
                continue
            for m_kw in pat.finditer(text):
                idx = m_kw.start()
                kw_len = len(m_kw.group(0))
                window_end = idx + kw_len + max_search_chars
                if current_field and all_label_keywords:
                    next_label = _find_next_label_position(
                        text[idx + kw_len:], current_field, all_label_keywords
                    )
                    if next_label > 0:
                        window_end = min(window_end, idx + kw_len + next_label)
                window = text[idx + kw_len: window_end]
                result = _try_match_range(window)
                if result:
                    return result
            continue

        # String literal
        kw_lower = keyword.strip().lower()
        if not kw_lower:
            continue
        idx = text_lower.find(kw_lower)
        while idx != -1:
            window_end = idx + len(keyword) + max_search_chars
            if current_field and all_label_keywords:
                next_label = _find_next_label_position(
                    text[idx + len(keyword):], current_field, all_label_keywords
                )
                if next_label > 0:
                    window_end = min(window_end, idx + len(keyword) + next_label)

            window = text[idx + len(keyword): window_end]
            result = _try_match_range(window)
            if result:
                return result

            idx = text_lower.find(kw_lower, idx + 1)

    return {"low": None, "high": None, "raw": None}


def find_all_reference_ranges(text: str, label_keywords_map: dict) -> dict:
    ranges = {}
    for field, keywords in label_keywords_map.items():
        ranges[field] = find_reference_range_for_field(
            text, keywords,
            current_field=field,
            all_label_keywords=label_keywords_map,
        )
    return ranges


def status_for_value(value, ref_range: dict) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "missing"
    if ref_range is None:
        return "unknown"

    low, high = ref_range.get("low"), ref_range.get("high")
    if low is None and high is None:
        return "unknown"

    if low is not None and value < low:
        return "low"
    if high is not None and value > high:
        return "high"

    if low is not None and high is not None:
        margin = 0.10 * (high - low)
        if value <= low + margin or value >= high - margin:
            return "borderline"

    return "normal"


def is_value_plausible_for_range(value, ref_range: dict, tolerance: float = 5.0) -> bool:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return True
    if ref_range is None:
        return True
    low, high = ref_range.get("low"), ref_range.get("high")
    if low is None and high is None:
        return True

    if low is not None and value < low / tolerance:
        return False
    if high is not None and value > high * tolerance:
        return False
    return True