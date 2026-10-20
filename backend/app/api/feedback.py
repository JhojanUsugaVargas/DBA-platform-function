"""Feedback Endpoints."""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.repositories import feedback_repo
from app.schemas.feedback import FeedbackSubmitRequest

router = APIRouter()


@router.post("/submit", summary="Submit user feedback")
def submit_feedback(
    req: FeedbackSubmitRequest,
    db: Session = Depends(get_db),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Save feedback rating (1-5) and comment. Free text travels in the body, never in the URL."""
    if not req.consent_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes autorizar el tratamiento de tu comentario para enviarlo."
        )
    feedback_repo.add_feedback(db, user["username"], req.rating, req.comment)
    return {"success": True, "message": "Feedback recibido exitosamente"}
