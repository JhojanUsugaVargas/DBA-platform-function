"""Authentication and Profile Endpoints."""
import time
import random
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.security import verify_password, get_password_hash, create_access_token
from app.db.session import get_db
from app.repositories import user_repo
from app.schemas.auth import (
    TokenResponse,
    VerifyOtpRequest,
    UpdatePasswordRequest,
    UpdatePhotoRequest,
    ToggleMFARequest,
    UserProfileResponse
)
from app.services.email_service import send_otp_email

router = APIRouter()

# In-memory OTP storage: username -> {"code": str, "expires": float}
_otp_store: Dict[str, Dict[str, Any]] = {}

# OWASP A04/A07: In-memory sliding window for brute force defense
_failed_login_attempts: Dict[str, list] = {}
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 60


@router.post("/login", response_model=TokenResponse, summary="User login, returns JWT token or MFA challenge")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Authenticate username and password with brute force protection."""
    username_key = form_data.username.strip().lower()
    now = time.time()

    # Clean up window and check threshold
    attempts = [t for t in _failed_login_attempts.get(username_key, []) if now - t < LOCKOUT_SECONDS]
    _failed_login_attempts[username_key] = attempts
    if len(attempts) >= MAX_FAILED_ATTEMPTS:
        remaining = int(LOCKOUT_SECONDS - (now - attempts[0]))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Demasiados intentos fallidos. Bloqueo de seguridad activo: espera {max(1, remaining)} segundos."
        )

    user = user_repo.get_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        _failed_login_attempts.setdefault(username_key, []).append(now)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )

    # Success: reset attempts
    _failed_login_attempts.pop(username_key, None)

    if user.mfa_enabled:
        return TokenResponse(access_token="pending", token_type="bearer", requires_mfa=True)

    token = create_access_token({"sub": user.username})
    return TokenResponse(access_token=token, token_type="bearer", requires_mfa=False)


@router.post("/send-otp", summary="Generate and send OTP code")
def send_otp(username: str, db: Session = Depends(get_db)):
    """Generate and dispatch OTP via email or console."""
    user = user_repo.get_by_username(db, username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    code = f"{random.randint(1000, 9999)}"
    _otp_store[username] = {
        "code": code,
        "expires": time.time() + settings.OTP_EXPIRE_SECONDS
    }

    # If SMTP is configured, attempt sending email
    if settings.SMTP_USER:
        dest_email = settings.SMTP_USER  # Or user-associated email
        sent = send_otp_email(dest_email, code)
        logging.info(f"OTP dispatch status to {dest_email}: {'SUCCESS' if sent else 'FALLBACK_LOG'}")

    logging.info(f"OTP temporal generado para '{username}': {code}")
    return {"message": "OTP enviado correctamente", "expires_in": settings.OTP_EXPIRE_SECONDS}


@router.post("/verify-otp", response_model=TokenResponse, summary="Verify OTP and return access token")
def verify_otp(req: VerifyOtpRequest, db: Session = Depends(get_db)):
    """Validate submitted OTP."""
    record = _otp_store.get(req.username)
    if not record:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No se ha solicitado OTP o expiró")

    if record["code"] != req.code:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Código OTP incorrecto")

    if time.time() > record["expires"]:
        _otp_store.pop(req.username, None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El código ha expirado")

    user = user_repo.get_by_username(db, req.username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    _otp_store.pop(req.username, None)
    token = create_access_token({"sub": user.username})
    return TokenResponse(access_token=token, token_type="bearer", requires_mfa=False)


@router.get("/profile/me", response_model=UserProfileResponse, summary="Get current user profile")
def get_profile(db: Session = Depends(get_db), current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get authenticated user profile."""
    user = user_repo.get_by_username(db, current_user["username"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return UserProfileResponse(
        username=user.username,
        full_name=user.full_name or user.username,
        role=user.role or "Monitor",
        mfa_enabled=user.mfa_enabled,
        profile_photo=user.profile_photo
    )


@router.put("/profile/password", summary="Change current user password")
def change_password(
    req: UpdatePasswordRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update current user password."""
    user = user_repo.get_by_username(db, current_user["username"])
    if not user or not verify_password(req.old_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Contraseña actual incorrecta")

    user.hashed_password = get_password_hash(req.new_password)
    db.commit()
    return {"message": "Contraseña actualizada con éxito"}


@router.put("/profile/photo", summary="Update profile photo")
def update_photo(
    req: UpdatePhotoRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update user avatar photo base64."""
    user = user_repo.get_by_username(db, current_user["username"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    user.profile_photo = req.photo_base64
    db.commit()
    return {"message": "Foto de perfil actualizada"}


@router.put("/profile/mfa", summary="Toggle Multi-Factor Authentication")
def toggle_mfa(
    req: ToggleMFARequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Enable or disable MFA challenge for login."""
    user = user_repo.get_by_username(db, current_user["username"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    user.mfa_enabled = req.mfa_enabled
    db.commit()
    return {"message": f"MFA {'activado' if req.mfa_enabled else 'desactivado'}"}
