"""ChatMessage Model."""
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.core.config import settings

_schema_args = {"schema": settings.DB_SCHEMA} if "postgresql" in settings.DATABASE_URL and settings.DB_SCHEMA else {}
_schema_prefix = f"{settings.DB_SCHEMA}." if "postgresql" in settings.DATABASE_URL and settings.DB_SCHEMA else ""


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = _schema_args

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(f"{_schema_prefix}users.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    content = Column(Text, nullable=False)

    # Relationships
    user = relationship("User", back_populates="chat_messages")
