"""Maintenance Window (Blackout Period) Model for Alert Silencing."""
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base
from app.core.config import settings

_schema_args = {"schema": settings.DB_SCHEMA} if "postgresql" in settings.DATABASE_URL and settings.DB_SCHEMA else {}


class MaintenanceWindow(Base):
    """Scheduled window during which proactive alerts and notifications are silenced."""
    __tablename__ = "maintenance_windows"
    __table_args__ = _schema_args

    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(Integer, nullable=True, index=True)  # Null = All instances / Global
    title = Column(String(150), nullable=False)
    reason = Column(Text, nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(String(50), nullable=False, default="admin")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
