"""Feedback Schemas."""
from typing import Optional
from pydantic import BaseModel, Field


class FeedbackSubmitRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None
