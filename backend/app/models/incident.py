"""Support Incident and Requirement Ticket Model."""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.db.base import Base
from app.core.config import settings

_schema_args = {"schema": settings.DB_SCHEMA} if "postgresql" in settings.DATABASE_URL and settings.DB_SCHEMA else {}
_schema_prefix = f"{settings.DB_SCHEMA}." if "postgresql" in settings.DATABASE_URL and settings.DB_SCHEMA else ""


class Incident(Base):
    """Support and maintenance incident tickets."""
    __tablename__ = "incidents"
    __table_args__ = _schema_args

    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String(30), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey(f"{_schema_prefix}users.id", ondelete="SET NULL"), nullable=True)
    instance_id = Column(Integer, ForeignKey(f"{_schema_prefix}instances.id", ondelete="SET NULL"), nullable=True)
    ticket_type = Column(String(30), default="Incidente", nullable=False)  # Incidente, Requerimiento, Soporte
    module = Column(String(50), default="General", nullable=False)
    priority = Column(String(20), default="Media", nullable=False)        # Baja, Media, Alta, Crítica
    status = Column(String(30), default="Abierto", nullable=False)         # Abierto, En Progreso, Resuelto, Cerrado
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    notes = Column(Text, nullable=True)
    assigned_to = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
