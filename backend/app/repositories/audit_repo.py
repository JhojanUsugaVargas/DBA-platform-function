"""Audit Repository."""
from typing import List, Dict, Any, Optional
import logging
from sqlalchemy.orm import Session
from app.models.audit import AuditLog
from app.models.user import User


def log_action(
    db: Session,
    username: str,
    action: str,
    engine: Optional[str] = None,
    target_spid: Optional[int] = None,
    instance_name: Optional[str] = None,
    contract_name: Optional[str] = None,
    status: str = "SUCCESS",
    details: Optional[str] = None
) -> Optional[int]:
    """Records an administrative audit event."""
    try:
        user = db.query(User).filter(User.username == username).first()
        user_id = user.id if user else None

        log = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            engine=engine,
            target_spid=target_spid,
            instance_name=instance_name,
            contract_name=contract_name,
            status=status,
            details=details
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log.id
    except Exception as exc:
        db.rollback()
        logging.error(f"Error logging audit action {action} for {username}: {exc}")
        return None


def get_audit_logs(db: Session, limit: int = 100, action: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve historical audit records."""
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()

    return [
        {
            "id": l.id,
            "username": l.username,
            "action": l.action,
            "engine": l.engine,
            "target_spid": l.target_spid,
            "instance_name": l.instance_name,
            "contract_name": l.contract_name,
            "status": l.status,
            "details": l.details,
            "timestamp": str(l.timestamp) if l.timestamp else None,
        }
        for l in logs
    ]
