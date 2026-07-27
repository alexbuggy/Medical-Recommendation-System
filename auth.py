import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import User, get_db

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-secret-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 ore

if SECRET_KEY == "change-this-secret-in-production":
    print("  WARNING: folosești JWT_SECRET_KEY default. Setează unul în .env!")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token invalid: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Necesită autentificare",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, "Token invalid (lipsește sub)")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(401, "User inexistent")
    if not user.is_active:
        raise HTTPException(403, "Cont neactivat")
    return user


def require_medic(user: User = Depends(get_current_user)) -> User:
    if user.role != "medic":
        raise HTTPException(403, "Necesită rol medic")
    return user


def require_patient(user: User = Depends(get_current_user)) -> User:
    if user.role != "patient":
        raise HTTPException(403, "Necesită rol pacient")
    return user

ACTIVATION_CODE_LIFETIME_HOURS = 48


def generate_activation_code() -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(6))


def generate_temp_password() -> str:
    return secrets.token_urlsafe(12)