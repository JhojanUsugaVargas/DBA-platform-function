"""User Session and Preferences Model."""
from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.db.base import Base
from app.core.config import settings

_schema_args = {"schema": settings.DB_SCHEMA} if "postgresql" in settings.DATABASE_URL and settings.DB_SCHEMA else {}
_schema_prefix = f"{settings.DB_SCHEMA}." if "postgresql" in settings.DATABASE_URL and settings.DB_SCHEMA else ""


class UserPreference(Base):
    """Stores user's last selected instance, contract and interface state."""
    __tablename__ = "user_preferences"
    __table_args__ = _schema_args

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(f"{_schema_prefix}users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    selected_contract_id = Column(Integer, ForeignKey(f"{_schema_prefix}contracts.id", ondelete="SET NULL"), nullable=True)
    selected_instance_id = Column(Integer, ForeignKey(f"{_schema_prefix}instances.id", ondelete="SET NULL"), nullable=True)
    last_active_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
