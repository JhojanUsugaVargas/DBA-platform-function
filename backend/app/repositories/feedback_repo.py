"""Feedback Repository."""
from typing import Optional
from sqlalchemy.orm import Session
from app.models.feedback import Feedback
from app.models.user import User


def add_feedback(db: Session, username: str, rating: int, comment: Optional[str] = None) -> int:
    """Store feedback or support ticket for user."""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise ValueError("Usuario no encontrado")

    fb = Feedback(user_id=user.id, rating=rating, comment=comment)
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb.id


def get_feedback_by_id(db: Session, feedback_id: int) -> Optional[Feedback]:
    """Retrieve feedback/ticket by ID."""
    return db.query(Feedback).filter(Feedback.id == feedback_id).first()
