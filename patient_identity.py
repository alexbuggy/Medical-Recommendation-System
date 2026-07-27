"""
patient_identity.py — Extragere CNP și nume pacient din textul unui PDF de analize.

CNP-ul românesc: 13 cifre. Structura: S AA LL ZZ JJ NNN C
  S    = sex + secol (1-8)
  AA   = anul nașterii (2 cifre)
  LL   = luna (01-12)
  ZZ   = ziua (01-31)
  JJ   = județul (01-52, sau 41-46/51-52 pt București)
  NNN  = număr secvențial
  C    = cifra de control

Validăm CNP-ul cu cifra de control — așa eliminăm numere de 13 cifre care
NU sunt CNP-uri reale (coduri de bare, numere de fișă, etc.).
"""

import re

# Cheia de control pentru validarea CNP (algoritm oficial)
CNP_CONTROL_KEY = [2, 7, 9, 1, 4, 6, 3, 5, 8, 2, 7, 9]


def validate_cnp(cnp: str) -> bool:
    """
    Verifică dacă un șir de 13 cifre e un CNP valid (cifra de control corectă).
    """
    clean = "".join(c for c in cnp if c.isdigit())
    if len(clean) != 13:
        return False

    # Calculează cifra de control
    total = sum(int(clean[i]) * CNP_CONTROL_KEY[i] for i in range(12))
    control = total % 11
    if control == 10:
        control = 1

    return control == int(clean[12])


def extract_cnp(text: str) -> str | None:
    """
    Caută un CNP valid în text.

    Strategie:
      1) Caută eticheta "CNP" și ia numărul de lângă ea (cel mai sigur)
      2) Dacă nu, caută orice secvență de 13 cifre care trece validarea
    """
    text_lower = text.lower()

    # Strategia 1: lângă eticheta "CNP"
    # Acceptă "CNP: 1234...", "CNP 1234...", "C.N.P. 1234..."
    label_patterns = [
        r"c\.?\s*n\.?\s*p\.?\s*[:\-]?\s*(\d[\d\s]{11,16}\d)",
        r"cod\s+numeric\s+personal\s*[:\-]?\s*(\d[\d\s]{11,16}\d)",
    ]
    for pat in label_patterns:
        for m in re.finditer(pat, text_lower):
            candidate = "".join(c for c in m.group(1) if c.isdigit())
            if len(candidate) == 13 and validate_cnp(candidate):
                return candidate

    # Strategia 2: orice secvență de exact 13 cifre care e CNP valid
    # Folosim word boundary ca să nu prindem 13 cifre dintr-un număr mai lung
    for m in re.finditer(r"(?<!\d)(\d{13})(?!\d)", text):
        candidate = m.group(1)
        if validate_cnp(candidate):
            return candidate

    return None


def extract_patient_name(text: str) -> str | None:
    """
    Caută numele pacientului în text.

    Laboratoarele afișează de obicei "Nume:", "Pacient:", "Nume și prenume:" etc.
    Numele românesc are 2-4 cuvinte, fiecare începând cu majusculă.

    NOTĂ: extragerea numelui e mai puțin sigură decât CNP-ul. Medicul oricum
    va valida totul pe ecranul de confirmare.
    """
    # Cuvinte care NU pot face parte dintr-un nume (etichete care urmează numelui)
    BLACKLIST_WORDS = {
        "cnp", "cod", "data", "varsta", "vârsta", "sex", "adresa", "adresă",
        "telefon", "email", "medic", "analiz", "rezultat", "laborator",
        "buletin", "cabinet", "clinica", "clinică", "spital", "nascut",
        "născut", "nr", "fisa", "fișa",
    }

    # Procesăm linie cu linie ca să nu trecem peste sfârșitul rândului
    lines = text.split("\n")
    label_res = [
        re.compile(r"nume\s+(?:și|si)\s+prenume\s*[:\-]?\s*(.+)", re.IGNORECASE),
        re.compile(r"nume\s+pacient\s*[:\-]?\s*(.+)", re.IGNORECASE),
        re.compile(r"pacient\s*[:\-]?\s*(.+)", re.IGNORECASE),
        re.compile(r"nume\s*[:\-]?\s*(.+)", re.IGNORECASE),
    ]

    for pat in label_res:
        for line in lines:
            m = pat.search(line)
            if not m:
                continue
            rest = m.group(1).strip()

            # Ia doar cuvintele capitalizate de la început, oprește la primul
            # cuvânt din blacklist sau la primul non-nume
            words = rest.split()
            name_words = []
            for w in words:
                w_clean = w.strip(".,;:()-")
                if not w_clean:
                    break
                # Oprește la blacklist
                if w_clean.lower() in BLACKLIST_WORDS:
                    break
                # Oprește dacă conține cifre
                if any(c.isdigit() for c in w_clean):
                    break
                # Trebuie să înceapă cu majusculă (nume propriu)
                if not w_clean[0].isupper():
                    break
                name_words.append(w_clean)
                # Max 4 cuvinte într-un nume
                if len(name_words) >= 4:
                    break

            if len(name_words) >= 2:  # nume + cel puțin un prenume
                return " ".join(w.capitalize() for w in name_words)

    return None


def extract_patient_identity(text: str) -> dict:
    """
    Extrage identitatea pacientului din textul PDF-ului.

    Returnează:
        {"cnp": str|None, "name": str|None, "cnp_valid": bool}
    """
    cnp = extract_cnp(text)
    name = extract_patient_name(text)
    return {
        "cnp": cnp,
        "name": name,
        "cnp_valid": cnp is not None,
    }


if __name__ == "__main__":
    # Test rapid
    sample = """
    BULETIN DE ANALIZE MEDICALE
    Nume și prenume: Popescu Ion Gabriel
    CNP: 1900101411203
    Data recoltării: 15.05.2026

    Glicemie  92  mg/dL
    """
    result = extract_patient_identity(sample)
    print("Rezultat extragere identitate:")
    print(f"  Nume: {result['name']}")
    print(f"  CNP:  {result['cnp']}")
    print(f"  CNP valid: {result['cnp_valid']}")