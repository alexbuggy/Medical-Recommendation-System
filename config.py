"""
config.py — Central configuration and fail-fast secret loading.

All secrets and filesystem paths live here. Secrets are required: if a
critical one is missing (or left at a placeholder), the app refuses to
start rather than running with an insecure default.

Paths are anchored to this file's location, so the app runs correctly no
matter what directory it is launched from.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# PATHS — anchored to project root (this file's directory)
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
MODELS_DIR = Path(os.getenv("MODELS_DIR", BASE_DIR / "models"))
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", BASE_DIR / "uploads"))

MODEL_PATH = MODELS_DIR / "specialist_nn.keras"
PREP_PATH = MODELS_DIR / "nn_preprocessing.pkl"
DATASET_PATH = DATA_DIR / "dataset_accumulated.csv"

# Ensure runtime dirs exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# DATABASE
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'medrec.db'}")

# ---------------------------------------------------------------------------
# SECRETS — required, no insecure fallback
# ---------------------------------------------------------------------------

_PLACEHOLDERS = {
    "change-this-secret-in-production",
    "change-this-in-production",
    "",
}


def _require_secret(name: str) -> str:
    value = os.getenv(name, "")
    if value in _PLACEHOLDERS:
        sys.stderr.write(
            f"\nFATAL: {name} is missing or set to a placeholder.\n"
            f"Set a strong random value in your .env file. Generate one with:\n"
            f"  python -c \"import secrets; print(secrets.token_urlsafe(48))\"\n\n"
        )
        raise SystemExit(1)
    return value


JWT_SECRET_KEY = _require_secret("JWT_SECRET_KEY")
CNP_PEPPER = _require_secret("CNP_PEPPER")

# Gates /auth/register-medic. Medic is the privileged role, so registration
# is invite-only; without this the endpoint would be open to anyone.
MEDIC_INVITE_CODE = _require_secret("MEDIC_INVITE_CODE")

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 12)))

# ---------------------------------------------------------------------------
# OPENAI
# ---------------------------------------------------------------------------

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------

# On Linux/Docker tesseract is on PATH at /usr/bin/tesseract, so this is
# usually unset. Provided for Windows/local dev where the binary may be
# elsewhere. If set, pdf_utils points pytesseract at it.
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "")

# ---------------------------------------------------------------------------
# SMTP
# ---------------------------------------------------------------------------

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "MedRec")

# ---------------------------------------------------------------------------
# APP / ENVIRONMENT
# ---------------------------------------------------------------------------

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT.lower() == "production"

# Comma-separated allowlist for CORS. The default covers local dev only;
# a deployment sets CORS_ORIGINS to its real origin(s).
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080"
    ).split(",")
    if o.strip()
]
