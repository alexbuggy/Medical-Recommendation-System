
import os
import uuid
import shutil
import tempfile
import traceback
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, User, PatientProfile, Report
from auth import require_patient
from rate_limit import limiter

from pdf_utils import extract_medical_values

from model_service import (
    MODEL_FEATURES, PDF_EXTRACTABLE, USER_ONLY_FEATURES,
    clean_extracted, predict_with_explanation, generate_report,
)

router = APIRouter(prefix="/patient", tags=["patient"])


# ---------------------------------------------------------------------------
# SCHEMA: cele 23 feature-uri ale modelului
# ---------------------------------------------------------------------------

class SelfPredictRequest(BaseModel):
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

    use_gpt: bool = True


# ---------------------------------------------------------------------------
# ENDPOINT: ISTORIC RAPOARTE (saved by medic only)
# ---------------------------------------------------------------------------

@router.get("/reports")
def my_reports(patient: User = Depends(require_patient),
                db: Session = Depends(get_db)):
    """Istoricul rapoartelor pacientului — doar cele uploadate de medici."""
    profile = db.query(PatientProfile).filter(
        PatientProfile.user_id == patient.id
    ).first()
    if not profile:
        return {"patient_name": patient.full_name, "reports": []}

    reports = db.query(Report).filter(
        Report.patient_id == profile.id
    ).order_by(Report.created_at.desc()).all()

    return {
        "patient_name": patient.full_name,
        "reports": [
            {
                "report_id": r.id,
                "created_at": r.created_at.isoformat(),
                "final_specialist": r.final_specialist,
                "extracted_values": r.extracted_values,
                "report_text": r.report_text,
                "used_gpt": r.used_gpt,
            }
            for r in reports
        ],
    }


# ---------------------------------------------------------------------------
# ENDPOINT: SELF-EXTRACT (NU salveaza nimic)
# ---------------------------------------------------------------------------

@router.post("/self-extract")
@limiter.limit("10/minute")
async def self_extract(
    request: Request,
    file: UploadFile = File(...),
    use_gpt: bool = Form(True),
    patient: User = Depends(require_patient),
):
    """Pacientul incarca PDF/imagine -> extragere. NU se salveaza nimic."""
    try:
        ext = os.path.splitext(file.filename)[1].lower()
        tmp_path = os.path.join(tempfile.gettempdir(),
                                f"medrec_self_{uuid.uuid4().hex}{ext}")
        with open(tmp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Extragere unificata (PDF sau imagine)
        vals = extract_medical_values(tmp_path, use_gpt=use_gpt, verbose=False)

        # Cleanup imediat — nu pastram fisierul pe pacient
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except Exception:
            pass

        clean_vals = clean_extracted(vals)
        missing_extractable = [f for f, v in clean_vals.items() if v is None]

        return JSONResponse({
            "extracted_values": clean_vals,
            "missing_fields": missing_extractable,
            "user_only_fields": USER_ONLY_FEATURES,
            "used_gpt": use_gpt,
        })

    except Exception as e:
        # Clientul primeste doar un id de corelare; detaliile raman in log.
        error_id = uuid.uuid4().hex[:8]
        traceback.print_exc()
        print(f"[error_id={error_id}] {type(e).__name__}: {e}")
        return JSONResponse({"error": "Eroare internă", "error_id": error_id},
                             status_code=500)


# ---------------------------------------------------------------------------
# ENDPOINT: SELF-PREDICT (NU salveaza nimic)
# ---------------------------------------------------------------------------

@router.post("/self-predict")
async def self_predict(payload: SelfPredictRequest,
                        patient: User = Depends(require_patient)):
    """Pacientul confirma valorile -> NN + SHAP -> raport. NU se salveaza nimic."""
    try:
        # 1. Construieste dict-ul de 23 feature-uri
        values_dict = {f: getattr(payload, f) for f in MODEL_FEATURES}

        # 2. NN + SHAP
        result = predict_with_explanation(values_dict)
        recommended = result["specialist"]
        confidence = result["confidence"]
        top_factors = result["explanation"]["top_factors"]
        used_default = result["used_default"]

        # 3. Raport (cu toggle GPT)
        report_text, gpt_used = generate_report(
            values_dict, recommended,
            top_factors=top_factors, confidence=confidence,
            use_gpt=payload.use_gpt,
        )

        return JSONResponse({
            "recommended_specialist": recommended,
            "confidence": confidence,
            "probabilities": result["probabilities"],
            "explanation": result["explanation"],
            "report_text": report_text,
            "used_gpt": gpt_used,
            "campuri_completate_automat": used_default,
            "saved": False,
        })

    except Exception as e:
        # Clientul primeste doar un id de corelare; detaliile raman in log.
        error_id = uuid.uuid4().hex[:8]
        traceback.print_exc()
        print(f"[error_id={error_id}] {type(e).__name__}: {e}")
        raise HTTPException(500, f"Eroare internă (id: {error_id})")