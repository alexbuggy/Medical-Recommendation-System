import os
import hashlib
import uuid
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, String, Integer, Float, DateTime, Boolean,
    ForeignKey, JSON, Text, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from dotenv import load_dotenv

load_dotenv()


# SQLite default — fișier local în ./data/medrec.db.
# Pentru a comuta la PostgreSQL în producție: setează DATABASE_URL în .env la
# format postgresql://user:pass@host:5432/dbname. Codul rămâne identic.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/medrec.db")

# Pepper pentru CNP — un secret fixe care se adaugă la fiecare CNP înainte
# de hashare. Asta previne rainbow tables: dacă cineva fură doar baza de
# date, are nevoie ȘI de pepper-ul din .env ca să poată brute-force CNP-uri.
CNP_PEPPER = os.getenv("CNP_PEPPER", "change-this-in-production")
if CNP_PEPPER == "change-this-in-production":
    print("  WARNING: folosești CNP_PEPPER default. Setează unul în .env!")

# Asigură că folderul ./data există pentru SQLite
if DATABASE_URL.startswith("sqlite"):
    os.makedirs("data", exist_ok=True)
    # SQLite are nevoie de check_same_thread=False pentru FastAPI (async).
    # Pentru PostgreSQL nu se aplică — SQLAlchemy ignoră argumentele
    # incompatibile.
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def hash_cnp(cnp: str) -> str:
    """SHA-256 + pepper. Determinist — același CNP întotdeauna produce același hash."""
    if not cnp:
        return ""
    # Normalizează: elimină spații, doar cifre
    clean = "".join(c for c in cnp if c.isdigit())
    if len(clean) != 13:  # CNP românesc are exact 13 cifre
        raise ValueError(f"CNP invalid: {len(clean)} cifre (așteptam 13)")
    h = hashlib.sha256((clean + CNP_PEPPER).encode("utf-8")).hexdigest()
    return h


# ---------------------------------------------------------------------------
# MODELE
# ---------------------------------------------------------------------------

class User(Base):
    """Cont de utilizator (medic sau pacient)."""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # 'medic' | 'patient'
    full_name = Column(String, nullable=False)

    # Activare
    is_active = Column(Boolean, default=False, nullable=False)
    activation_code = Column(String, nullable=True)
    activation_code_expires = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Pentru pacienți: hash-ul CNP-ului (unic per pacient)
    patient_profile = relationship(
        "PatientProfile", back_populates="user", uselist=False,
        cascade="all, delete-orphan"
    )


class PatientProfile(Base):
    """Detalii suplimentare pentru pacient. Separat de User pentru a permite
    extragere ușoară (medicii au User dar nu au PatientProfile)."""
    __tablename__ = "patient_profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"),
                     unique=True, nullable=False)
    cnp_hash = Column(String, unique=True, nullable=False, index=True)

    user = relationship("User", back_populates="patient_profile")
    reports = relationship("Report", back_populates="patient",
                            cascade="all, delete-orphan")


class Report(Base):
    """O analiză medicală uploadată de un medic, atașată unui pacient."""
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String, ForeignKey("patient_profiles.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    uploaded_by_medic_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Stocăm calea către PDF-ul original
    pdf_path = Column(String, nullable=False)

    # Valorile extrase după confirmare medic (9 features ca JSON)
    extracted_values = Column(JSON, nullable=False)

    # Predicția modelului + eventual override de la medic
    recommended_specialist = Column(String, nullable=False)
    overridden_specialist = Column(String, nullable=True)

    # Raportul generat (GPT sau template offline)
    report_text = Column(Text, nullable=False)
    used_gpt = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    patient = relationship("PatientProfile", back_populates="reports")

    @property
    def final_specialist(self) -> str:
        """Specialistul efectiv (override are prioritate dacă există)."""
        return self.overridden_specialist or self.recommended_specialist


class MedicPatientLink(Base):
    """Care medici au tratat care pacienți. Permite medicilor să vadă
    lista de pacienți pe care i-au consultat (fără să vadă alți pacienți)."""
    __tablename__ = "medic_patients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    medic_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(String, ForeignKey("patient_profiles.id", ondelete="CASCADE"),
                         nullable=False)
    first_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("medic_id", "patient_id", name="uq_medic_patient"),
    )


# ---------------------------------------------------------------------------
# UTILITARI
# ---------------------------------------------------------------------------

def get_db():
    """Dependency FastAPI: yield o sesiune DB și o închide la sfârșit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Creează toate tabelele dacă nu există. Apelat la pornirea app-ului."""
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables initialized")


if __name__ == "__main__":
    # Run direct cu `python database.py` pentru a inițializa schema
    init_db()