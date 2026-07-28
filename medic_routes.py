
import os
import math
import time
import uuid
import shutil
import secrets
import tempfile
import traceback
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import (
    get_db, User, PatientProfile, Report, MedicPatientLink, hash_cnp
)
from auth import (
    require_medic, hash_password, generate_activation_code,
    generate_temp_password, ACTIVATION_CODE_LIFETIME_HOURS,
)
from email_service import send_activation_email
from patient_identity import extract_patient_identity

# Extragere unificata (PDF / imagine)
from pdf_utils import *

# Toate cele de model (sursa unica de adevar)
from model_service import (
    MODEL_FEATURES, PDF_EXTRACTABLE, VALID_SPECIALISTS,
    clean_extracted, build_full_feature_dict,
    predict_with_explanation, generate_report,
)

router = APIRouter(prefix="/medic", tags=["medic"])

UPLOADS_DIR = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Maps an opaque token -> server-side temp path from /extract.
# The client never supplies a filesystem path, preventing arbitrary
# file reads via /predict. In-process dict; a multi-instance deploy
# would use Redis or the DB instead.
_EXTRACT_TOKENS: dict[str, str] = {}


# ---------------------------------------------------------------------------
# SCHEMAS — cele 23 feature-uri ale modelului, explicite
# ---------------------------------------------------------------------------

class PredictRequest(BaseModel):
    # Cele 23 feature-uri ale modelului (None unde lipseste)
    age: Optional[float] = None
    sex: Optional[float] = None
    alt: Optional[float] = None
    ast: Optional[float] = None
    bilirubin_total: Optional[float] = None
    bmi: Optional[float] = None
    bun: Optional[float] = None
    cholesterol_total: Optional[float] = None
    creatinine: Optional[float] = None
    diastolic_bp: Optional[float] = None
    egfr: Optional[float] = None
    glucose: Optional[float] = None
    hba1c: Optional[float] = None
    hdl: Optional[float] = None
    height_cm: Optional[float] = None
    hematocrit: Optional[float] = None
    hemoglobin: Optional[float] = None
    ldl: Optional[float] = None
    systolic_bp: Optional[float] = None
    triglycerides: Optional[float] = None
    wbc: Optional[float] = None
    weight_kg: Optional[float] = None
    oxygen_saturation: Optional[float] = None

    # Identitatea pacientului (confirmata/corectata de medic)
    patient_name: str
    patient_cnp: str
    patient_email: str

    # Optiuni
    use_gpt: bool = True
    override_specialist: Optional[str] = None

    # Token opac emis de /extract (nu o cale de fisier)
    upload_token: str


class OverrideRequest(BaseModel):
    specialist: str


# ---------------------------------------------------------------------------
# ENDPOINT 1: EXTRACT
# ---------------------------------------------------------------------------

@router.post("/extract")
async def medic_extract(
    file: UploadFile = File(...),
    use_gpt: bool = Form(True),
    medic: User = Depends(require_medic),
):
    """Pasul 1: uploadeaza fisier, extrage tot ce poate."""
    try:
        ext = os.path.splitext(file.filename)[1].lower()
        tmp_path = os.path.join(tempfile.gettempdir(),
                                f"medrec_{uuid.uuid4().hex}{ext}")
        with open(tmp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Extragere unificata (auto-detecteaza PDF vs imagine)
        vals = extract_medical_values(tmp_path, use_gpt=use_gpt, verbose=False)

        # Text pentru identitate (CNP, nume)
        text = ""
        if ext == ".pdf":
            pdf_type, text = detect_pdf_type(tmp_path)
            if pdf_type == "scan":
                text = ocr_pdf_with_tesseract(tmp_path, verbose=False)

        identity = extract_patient_identity(text) if text else {
            "cnp": None, "name": None, "cnp_valid": False
        }

        clean_vals = clean_extracted(vals)
        missing_extractable = [f for f, v in clean_vals.items() if v is None]

        upload_token = secrets.token_urlsafe(24)
        _EXTRACT_TOKENS[upload_token] = {
            "medic_id": medic.id, "path": tmp_path, "created": time.time()}

        return JSONResponse({
            "extracted_values": clean_vals,           # cele extractabile (19)
            "missing_fields": missing_extractable,    # din cele extractabile
            "user_only_fields": ["height_cm", "weight_kg", "bmi",
                                  "oxygen_saturation"],
            "patient_name": identity["name"],
            "patient_cnp": identity["cnp"],
            "cnp_valid": identity["cnp_valid"],
            "upload_token": upload_token,
            "used_gpt": use_gpt,
        })

    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# ENDPOINT 2: PREDICT + SAVE
# ---------------------------------------------------------------------------

@router.post("/predict")
async def medic_predict(payload: PredictRequest,
                          medic: User = Depends(require_medic),
                          db: Session = Depends(get_db)):
    """Pasul 2: model NN + SHAP, salvare raport, creare pacient daca e nou."""
    try:
        # 1. Valideaza CNP
        try:
            cnp_h = hash_cnp(payload.patient_cnp)
        except ValueError as e:
            raise HTTPException(400, f"CNP invalid: {e}")

        # 2. Construieste dict-ul de 23 feature-uri
        values_dict = {f: getattr(payload, f) for f in MODEL_FEATURES}

        # 3. Ruleaza NN + SHAP (completeaza automat valorile lipsa cu default)
        result = predict_with_explanation(values_dict)
        recommended = result["specialist"]
        confidence = result["confidence"]
        top_factors = result["explanation"]["top_factors"]
        used_default = result["used_default"]

        # 4. Override medic (validat impotriva celor 6 clase)
        overridden = None
        if payload.override_specialist:
            if payload.override_specialist not in VALID_SPECIALISTS:
                raise HTTPException(
                    400, f"Specialist invalid: {payload.override_specialist}. "
                         f"Valide: {VALID_SPECIALISTS}")
            if payload.override_specialist != recommended:
                overridden = payload.override_specialist
        final_specialist = overridden or recommended

        # 5. Raport — folosind SHAP, cu toggle GPT
        report_text, gpt_used = generate_report(
            values_dict, final_specialist,
            top_factors=top_factors, confidence=confidence,
            use_gpt=payload.use_gpt,
        )

        # 6. Gaseste sau creeaza pacientul
        patient_profile = db.query(PatientProfile).filter(
            PatientProfile.cnp_hash == cnp_h
        ).first()
        is_new_patient = patient_profile is None
        activation_code = None

        if is_new_patient:
            existing_email = db.query(User).filter(
                User.email == payload.patient_email.lower()
            ).first()
            if existing_email:
                raise HTTPException(
                    400, f"Email {payload.patient_email} deja folosit")

            activation_code = generate_activation_code()
            patient_user = User(
                email=payload.patient_email.lower(),
                password_hash=hash_password(generate_temp_password()),
                role="patient",
                full_name=payload.patient_name,
                is_active=False,
                activation_code=activation_code,
                activation_code_expires=datetime.utcnow() + timedelta(
                    hours=ACTIVATION_CODE_LIFETIME_HOURS),
            )
            db.add(patient_user)
            db.flush()

            patient_profile = PatientProfile(
                user_id=patient_user.id, cnp_hash=cnp_h)
            db.add(patient_profile)
            db.flush()

        # 7. Salveaza PDF-ul permanent
        patient_uploads = os.path.join(UPLOADS_DIR, patient_profile.id)
        os.makedirs(patient_uploads, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        # Resolve the token to a server-held path. The client cannot
        # supply a path, only a token we issued. .pop makes it single-use.
        entry = _EXTRACT_TOKENS.get(payload.upload_token)
        if (not entry or entry["medic_id"] != medic.id
                or time.time() - entry["created"] > 3600
                or not os.path.exists(entry["path"])):
            raise HTTPException(400, "Upload token invalid sau expirat")
        tmp_src = entry["path"]
        _EXTRACT_TOKENS.pop(payload.upload_token, None)
        pdf_ext = os.path.splitext(tmp_src)[1] or ".pdf"
        final_pdf_path = os.path.join(patient_uploads, f"{timestamp}{pdf_ext}")
        shutil.move(tmp_src, final_pdf_path)

        # 8. Salveaza raportul (extracted_values = 23 feature-uri, JSON in DB)
        # Adaugam si explicatia SHAP pentru audit
        stored_values = {f: values_dict[f] for f in MODEL_FEATURES}
        report = Report(
            patient_id=patient_profile.id,
            uploaded_by_medic_id=medic.id,
            pdf_path=final_pdf_path,
            extracted_values=stored_values,
            recommended_specialist=recommended,
            overridden_specialist=overridden,
            report_text=report_text,
            used_gpt=gpt_used,
        )
        db.add(report)

        # 9. Linkeaza medicul cu pacientul
        link = db.query(MedicPatientLink).filter(
            MedicPatientLink.medic_id == medic.id,
            MedicPatientLink.patient_id == patient_profile.id,
        ).first()
        if not link:
            db.add(MedicPatientLink(
                medic_id=medic.id, patient_id=patient_profile.id))

        db.commit()
        db.refresh(report)

        # 10. Email activare pentru pacient nou
        email_sent = False
        if is_new_patient and activation_code:
            email_sent = send_activation_email(
                payload.patient_email, payload.patient_name, activation_code)

        return JSONResponse({
            "report_id": report.id,
            "recommended_specialist": recommended,
            "final_specialist": final_specialist,
            "overridden": overridden is not None,
            "confidence": confidence,
            "probabilities": result["probabilities"],
            "explanation": result["explanation"],
            "report_text": report_text,
            "used_gpt": gpt_used,
            "campuri_completate_automat": used_default,
            "is_new_patient": is_new_patient,
            "activation_email_sent": email_sent,
        })

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        db.rollback()
        raise HTTPException(500, str(e))


# ---------------------------------------------------------------------------
# ENDPOINT 3: LISTA PACIENTI
# ---------------------------------------------------------------------------

@router.get("/patients")
def list_patients(medic: User = Depends(require_medic),
                   db: Session = Depends(get_db)):
    links = db.query(MedicPatientLink).filter(
        MedicPatientLink.medic_id == medic.id).all()

    result = []
    for link in links:
        profile = db.query(PatientProfile).filter(
            PatientProfile.id == link.patient_id).first()
        if not profile:
            continue
        patient_user = db.query(User).filter(User.id == profile.user_id).first()
        report_count = db.query(Report).filter(
            Report.patient_id == profile.id).count()
        result.append({
            "patient_id": profile.id,
            "name": patient_user.full_name if patient_user else "?",
            "email": patient_user.email if patient_user else "?",
            "is_active": patient_user.is_active if patient_user else False,
            "report_count": report_count,
            "first_seen": link.first_seen_at.isoformat(),
        })
    result.sort(key=lambda x: x["name"])
    return {"patients": result}


# ---------------------------------------------------------------------------
# ENDPOINT 4: ISTORIC PACIENT
# ---------------------------------------------------------------------------

@router.get("/patient/{patient_id}")
def patient_history(patient_id: str, medic: User = Depends(require_medic),
                     db: Session = Depends(get_db)):
    link = db.query(MedicPatientLink).filter(
        MedicPatientLink.medic_id == medic.id,
        MedicPatientLink.patient_id == patient_id).first()
    if not link:
        raise HTTPException(403, "Nu ai acces la acest pacient")

    profile = db.query(PatientProfile).filter(
        PatientProfile.id == patient_id).first()
    if not profile:
        raise HTTPException(404, "Pacient inexistent")

    patient_user = db.query(User).filter(User.id == profile.user_id).first()
    reports = db.query(Report).filter(
        Report.patient_id == patient_id).order_by(
        Report.created_at.desc()).all()

    return {
        "patient": {
            "id": profile.id,
            "name": patient_user.full_name if patient_user else "?",
            "email": patient_user.email if patient_user else "?",
            "is_active": patient_user.is_active if patient_user else False,
        },
        "reports": [
            {
                "report_id": r.id,
                "created_at": r.created_at.isoformat(),
                "recommended_specialist": r.recommended_specialist,
                "final_specialist": r.final_specialist,
                "overridden": r.overridden_specialist is not None,
                "extracted_values": r.extracted_values,
                "report_text": r.report_text,
                "used_gpt": r.used_gpt,
                "has_pdf": bool(r.pdf_path),
            }
            for r in reports
        ],
    }


# ---------------------------------------------------------------------------
# ENDPOINT 5: DESCARCA PDF
# ---------------------------------------------------------------------------

@router.get("/report/{report_id}/pdf")
def download_report_pdf(report_id: str, medic: User = Depends(require_medic),
                         db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Raport inexistent")
    link = db.query(MedicPatientLink).filter(
        MedicPatientLink.medic_id == medic.id,
        MedicPatientLink.patient_id == report.patient_id).first()
    if not link:
        raise HTTPException(403, "Nu ai acces la acest raport")
    if not report.pdf_path or not os.path.exists(report.pdf_path):
        raise HTTPException(404, "PDF indisponibil")
    return FileResponse(report.pdf_path, filename=os.path.basename(report.pdf_path))


# ---------------------------------------------------------------------------
# ENDPOINT 6: OVERRIDE SPECIALIST
# ---------------------------------------------------------------------------

@router.post("/report/{report_id}/override")
def override_specialist(report_id: str, payload: OverrideRequest,
                          medic: User = Depends(require_medic),
                          db: Session = Depends(get_db)):
    if payload.specialist not in VALID_SPECIALISTS:
        raise HTTPException(
            400, f"Specialist invalid: {payload.specialist}. "
                 f"Valide: {VALID_SPECIALISTS}")

    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Raport inexistent")

    link = db.query(MedicPatientLink).filter(
        MedicPatientLink.medic_id == medic.id,
        MedicPatientLink.patient_id == report.patient_id).first()
    if not link:
        raise HTTPException(403, "Nu ai acces la acest raport")

    if payload.specialist == report.recommended_specialist:
        report.overridden_specialist = None
    else:
        report.overridden_specialist = payload.specialist
    db.commit()

    return {
        "report_id": report.id,
        "recommended_specialist": report.recommended_specialist,
        "final_specialist": report.final_specialist,
        "overridden": report.overridden_specialist is not None,
    }