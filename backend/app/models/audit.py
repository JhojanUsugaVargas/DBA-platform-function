"""AuditLog Model for tracking critical DBA operations."""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.core.config import settings

_schema_args = {"schema": settings.DB_SCHEMA} if "postgresql" in settings.DATABASE_URL and settings.DB_SCHEMA else {}
_schema_prefix = f"{settings.DB_SCHEMA}." if "postgresql" in settings.DATABASE_URL and settings.DB_SCHEMA else ""


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = _schema_args

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(f"{_schema_prefix}users.id"), nullable=True)
    username = Column(String(100), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)  # e.g. "KILL_TRANSACTION", "CREATE_INSTANCE", "CREATE_CONTRACT"
    engine = Column(String(50), nullable=True)  # "SQL SERVER", "POSTGRESQL"
    target_spid = Column(Integer, nullable=True)  # SPID / PID killed
    instance_name = Column(String(100), nullable=True)
    contract_name = Column(String(100), nullable=True)
    status = Column(String(30), nullable=False, default="SUCCESS")  # "SUCCESS", "FAILED", "UNAUTHORIZED"
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="audit_logs")
