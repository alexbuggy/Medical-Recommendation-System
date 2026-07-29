from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from database import User, get_db
from auth import (
    hash_password, verify_password, create_access_token,
    get_current_user,
)
from rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["auth"])

class MedicRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2)


class ActivateRequest(BaseModel):
    email: EmailStr
    activation_code: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=8)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    full_name: str

@router.post("/register-medic", response_model=LoginResponse)
def register_medic(payload: MedicRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(400, "Email deja înregistrat")

    medic = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role="medic",
        full_name=payload.full_name,
        is_active=True,
    )
    db.add(medic)
    db.commit()
    db.refresh(medic)

    token = create_access_token(medic.id, medic.role)
    return LoginResponse(
        access_token=token,
        user_id=medic.id,
        role=medic.role,
        full_name=medic.full_name,
    )


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username.lower()).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(401, "Email sau parolă greșită")
    if not user.is_active:
        raise HTTPException(403, "Cont neactivat — verifică emailul pentru codul de activare")

    token = create_access_token(user.id, user.role)
    return LoginResponse(
        access_token=token,
        user_id=user.id,
        role=user.role,
        full_name=user.full_name,
    )


@router.post("/activate", response_model=LoginResponse)
@limiter.limit("3/hour")
def activate(request: Request, payload: ActivateRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user:
        raise HTTPException(404, "Cont inexistent")
    if user.is_active:
        raise HTTPException(400, "Cont deja activ")
    if not user.activation_code or user.activation_code != payload.activation_code:
        raise HTTPException(400, "Cod activare incorect")
    if user.activation_code_expires and user.activation_code_expires < datetime.utcnow():
        raise HTTPException(400, "Cod activare expirat — cere medicului unul nou")

    user.password_hash = hash_password(payload.new_password)
    user.is_active = True
    user.activation_code = None
    user.activation_code_expires = None
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.role)
    return LoginResponse(
        access_token=token,
        user_id=user.id,
        role=user.role,
        full_name=user.full_name,
    )


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "full_name": user.full_name,
        "created_at": user.created_at.isoformat(),
    }