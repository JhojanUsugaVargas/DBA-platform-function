"""Authentication and Profile Endpoints."""
import time
import random
import logging
from html import escape
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from datetime import datetime, timezone
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_unsubscribe_token,
)
from app.db.session import get_db
from app.models.user import User
from app.repositories import user_repo, audit_repo
from app.schemas.auth import (
    TokenResponse,
    VerifyOtpRequest,
    UpdatePasswordRequest,
    UpdatePhotoRequest,
    ToggleMFARequest,
    DeleteAccountRequest,
    UserProfileResponse
)
from app.services.email_service import send_otp_email
from app.services import privacy_service

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

    token = create_access_token({"sub": user.username, "role": user.role})
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

    # If SMTP is configured, send to the user's own mailbox (fallback: service mailbox)
    if settings.SMTP_USER:
        dest_email = user.email or settings.SMTP_USER
        sent = send_otp_email(dest_email, code)
        logging.info(f"OTP dispatch status for '{username}': {'SUCCESS' if sent else 'FALLBACK_LOG'}")
        if not sent:
            logging.info(f"OTP temporal generado para '{username}': {code}")
    else:
        # Development without SMTP: the code is only visible in the server console
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
    token = create_access_token({"sub": user.username, "role": user.role})
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
        profile_photo=user.profile_photo,
        email_opt_out=bool(user.email_opt_out),
        consent_required=privacy_service.consent_required(user),
        legal_version=settings.LEGAL_VERSION,
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

    photo = req.photo_base64 or ""
    if photo:
        if not req.rights_confirmed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debes declarar que tienes derechos para usar la imagen."
            )
        allowed = ("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/jpg;base64,", "data:image/webp;base64,")
        if not photo.startswith(allowed):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de imagen no permitido (PNG, JPG o WebP)."
            )

    user.profile_photo = photo or None
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


# ---------------------------------------------------------------------------
# Privacy rights (Ley 1581 de 2012): consent, access/portability, erasure, opt-out
# ---------------------------------------------------------------------------

@router.post("/profile/consent", summary="Record acceptance of the current legal documents")
def accept_legal_documents(
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Store evidence (version + timestamp) of the user's authorization."""
    user = user_repo.get_by_username(db, current_user["username"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    privacy_service.record_consent(db, user)
    audit_repo.log_action(
        db=db, username=user.username, action="ACCEPT_LEGAL", status="SUCCESS",
        details=f"Aceptó documentos legales versión {settings.LEGAL_VERSION}."
    )
    return {"message": "Autorización registrada", "legal_version": settings.LEGAL_VERSION}


@router.get("/profile/export", summary="Download all personal data held about the current user")
def export_my_data(
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Right of access / portability."""
    user = user_repo.get_by_username(db, current_user["username"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    audit_repo.log_action(db=db, username=user.username, action="EXPORT_DATA", status="SUCCESS",
                          details="Exportación de datos personales solicitada por el titular.")
    return privacy_service.export_user_data(db, user)


@router.post("/profile/delete-account", summary="Permanently delete the current user's account and personal data")
def delete_my_account(
    req: DeleteAccountRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Right of erasure. Requires password re-entry to prevent accidental or hijacked requests."""
    user = user_repo.get_by_username(db, current_user["username"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Contraseña incorrecta")

    is_admin = (user.role or "").strip().lower() in {"admin", "administrador"}
    if is_admin:
        other_admins = [
            u for u in user_repo.list_users(db)
            if u.id != user.id and (u.role or "").strip().lower() in {"admin", "administrador"}
        ]
        if not other_admins:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Eres el único administrador. Asigna otro administrador antes de eliminar tu cuenta."
            )

    alias = privacy_service.erase_user(db, user)
    audit_repo.log_action(db=db, username=alias, action="DELETE_ACCOUNT", status="SUCCESS",
                          details="Cuenta eliminada por su titular (datos personales suprimidos).")
    return {"success": True, "message": "Tu cuenta y tus datos personales fueron eliminados."}


@router.put("/profile/email-preferences", summary="Opt in/out of non-essential emails")
def set_email_preferences(
    opt_out: bool,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    user = user_repo.get_by_username(db, current_user["username"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    user.email_opt_out = opt_out
    user.email_opt_out_at = datetime.now(timezone.utc) if opt_out else None
    db.commit()
    return {"message": "Preferencias de correo actualizadas", "email_opt_out": opt_out}


def _unsubscribe_page(title: str, message: str) -> HTMLResponse:
    page = f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;background:#0a0a0a;color:#ededed;display:grid;place-items:center;min-height:100vh;margin:0}}
main{{max-width:480px;padding:32px;background:#141414;border:1px solid #3f3f46;border-radius:12px}}
h1{{font-size:20px;margin:0 0 12px}}p{{color:#c4c4cc;line-height:1.6}}a{{color:#67e8f9}}</style></head>
<body><main><h1>{escape(title)}</h1><p>{escape(message)}</p>
<p><a href="{escape(settings.FRONTEND_URL)}">Volver a DataCheck Pro</a></p></main></body></html>"""
    return HTMLResponse(content=page)


@router.api_route("/unsubscribe", methods=["GET", "POST"], response_class=HTMLResponse, summary="One-click email opt-out (no login required)")
def unsubscribe(token: str, db: Session = Depends(get_db)):
    """Opt out of non-essential emails. Security emails (OTP) are always delivered."""
    username = decode_unsubscribe_token(token)
    user = user_repo.get_by_username(db, username) if username else None
    if not user:
        return _unsubscribe_page(
            "Enlace no válido",
            f"El enlace es inválido o expiró. Escríbenos a {settings.PRIVACY_CONTACT_EMAIL} y lo gestionamos."
        )
    user.email_opt_out = True
    user.email_opt_out_at = datetime.now(timezone.utc)
    db.commit()
    audit_repo.log_action(db=db, username=user.username, action="EMAIL_OPT_OUT", status="SUCCESS",
                          details="Baja de correos no esenciales mediante enlace.")
    return _unsubscribe_page(
        "Te diste de baja",
        "Ya no recibirás correos informativos. Seguirás recibiendo los mensajes de seguridad "
        "indispensables (por ejemplo, códigos de verificación)."
    )
