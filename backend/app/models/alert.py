"""System Alert model for proactive monitoring."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from app.db.base import Base
from app.core.config import settings

_schema_args = {"schema": settings.DB_SCHEMA} if settings.DB_SCHEMA else {}


class SystemAlert(Base):
    """Stores proactive alerts triggered by telemetry anomalies or deadlocks."""
    __tablename__ = "system_alerts"
    __table_args__ = (
        Index("ix_system_alerts_instance_read", "instance_id", "is_read", "created_at"),
        _schema_args
    )

    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(Integer, ForeignKey(f"{settings.DB_SCHEMA}.instances.id" if settings.DB_SCHEMA else "instances.id", ondelete="CASCADE"), nullable=True)
    severity = Column(String(20), default="WARNING")  # CRITICAL, WARNING, INFO
    metric_name = Column(String(50), nullable=False)   # CPU, DEADLOCK, BUFFER_CACHE, CONNECTION
    current_value = Column(String(50), nullable=True)
    threshold_value = Column(String(50), nullable=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, index=True)
    email_dispatched = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
