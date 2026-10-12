"""Feedback Model."""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.core.config import settings

_schema_args = {"schema": settings.DB_SCHEMA} if "postgresql" in settings.DATABASE_URL and settings.DB_SCHEMA else {}
_schema_prefix = f"{settings.DB_SCHEMA}." if "postgresql" in settings.DATABASE_URL and settings.DB_SCHEMA else ""


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = _schema_args

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(f"{_schema_prefix}users.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1 - 5, or 0 for support ticket
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(50), default="Abierto")
    notes = Column(Text, default="")

    # Relationships
    user = relationship("User", back_populates="feedback")
