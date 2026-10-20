"""Privacy service: consent evidence, data export (access/portability) and erasure (supresion).

Aplica los derechos del titular de la Ley 1581 de 2012: conocer, actualizar, rectificar y suprimir.
"""
import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit import AuditLog
from app.models.chat import ChatMessage
from app.models.feedback import Feedback
from app.models.user import User


def anonymous_alias(user: User) -> str:
    """Stable, non-reversible alias used to keep audit trail integrity after erasure."""
    digest = hashlib.sha256(f"{user.id}:{user.username}:{settings.SECRET_KEY}".encode()).hexdigest()[:10]
    return f"usuario-eliminado-{digest}"


def record_consent(db: Session, user: User) -> None:
    """Persist acceptance of the current legal documents version (evidence of authorization)."""
    user.consent_version = settings.LEGAL_VERSION
    user.consent_accepted_at = datetime.now(timezone.utc)
    db.commit()


def consent_required(user: User) -> bool:
    return user.consent_version != settings.LEGAL_VERSION


def export_user_data(db: Session, user: User) -> Dict[str, Any]:
    """Return every personal datum the platform stores about the user (never the password hash)."""
    feedback = db.query(Feedback).filter(Feedback.user_id == user.id).all()
    chats = db.query(ChatMessage).filter(ChatMessage.user_id == user.id).all()
    audits = db.query(AuditLog).filter(
        (AuditLog.user_id == user.id) | (AuditLog.username == user.username)
    ).all()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "controller": {"name": settings.DATA_CONTROLLER_NAME, "contact": settings.PRIVACY_CONTACT_EMAIL},
        "legal_version": settings.LEGAL_VERSION,
        "profile": {
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "mfa_enabled": user.mfa_enabled,
            "has_profile_photo": bool(user.profile_photo),
            "consent_version": user.consent_version,
            "consent_accepted_at": str(user.consent_accepted_at) if user.consent_accepted_at else None,
            "email_opt_out": user.email_opt_out,
        },
        "feedback_and_tickets": [
            {
                "id": f.id,
                "rating": f.rating,
                "comment": f.comment,
                "status": f.status,
                "created_at": str(f.created_at) if f.created_at else None,
            }
            for f in feedback
        ],
        "chat_messages": [
            {"id": c.id, "content": c.content, "timestamp": str(c.timestamp) if c.timestamp else None}
            for c in chats
        ],
        "audit_trail": [
            {
                "id": a.id,
                "action": a.action,
                "status": a.status,
                "details": a.details,
                "timestamp": str(a.timestamp) if a.timestamp else None,
            }
            for a in audits
        ],
    }


def erase_user(db: Session, user: User) -> str:
    """Delete personal data of the user.

    - Account, profile photo, feedback/tickets and chat history are deleted (ORM cascade).
    - Audit records are kept for security/legal integrity but the identity is anonymized.
    Returns the anonymous alias used in the audit trail.
    """
    alias = anonymous_alias(user)
    original = user.username

    logs = db.query(AuditLog).filter(
        (AuditLog.user_id == user.id) | (AuditLog.username == original)
    ).all()
    for log in logs:
        log.user_id = None
        log.username = alias
        if log.details and original in log.details:
            log.details = log.details.replace(original, alias)
    if user.email:
        # Also scrub the email from other audit entries that mention it (e.g. CREATE_USER by an admin)
        mentions = db.query(AuditLog).filter(AuditLog.details.contains(user.email)).all()
        for log in mentions:
            log.details = log.details.replace(user.email, "[correo eliminado]")
    db.flush()

    db.delete(user)
    db.commit()
    logging.info(f"Datos personales suprimidos para {alias}.")
    return alias
