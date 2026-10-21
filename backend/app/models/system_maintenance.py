"""System Maintenance State Model."""
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from sqlalchemy.sql import func
from app.db.base import Base
from app.core.config import settings

_schema_args = {"schema": settings.DB_SCHEMA} if "postgresql" in settings.DATABASE_URL and settings.DB_SCHEMA else {}


class SystemMaintenance(Base):
    """Persistent maintenance lock status."""
    __tablename__ = "system_maintenance"
    __table_args__ = _schema_args

    id = Column(Integer, primary_key=True, index=True)
    is_active = Column(Boolean, default=False, nullable=False)
    title = Column(String(150), default="Ajustes del Sistema en Progreso", nullable=False)
    subtitle = Column(Text, default="Optimizando motores de bases de datos, reindexando y aplicando configuraciones DBA...", nullable=False)
    disabled_modules = Column(Text, default="[]", nullable=False)  # JSON-encoded string
    activated_by = Column(String(50), nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
