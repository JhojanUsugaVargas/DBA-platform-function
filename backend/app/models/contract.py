"""Contract and Instance Models."""
from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.core.config import settings

_schema_args = {"schema": settings.DB_SCHEMA} if "postgresql" in settings.DATABASE_URL and settings.DB_SCHEMA else {}
_schema_prefix = f"{settings.DB_SCHEMA}." if "postgresql" in settings.DATABASE_URL and settings.DB_SCHEMA else ""


class Contract(Base):
    __tablename__ = "contracts"
    __table_args__ = _schema_args

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)

    # Relationships
    instances = relationship("Instance", back_populates="contract", cascade="all, delete-orphan")


class Instance(Base):
    __tablename__ = "instances"
    __table_args__ = _schema_args

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey(f"{_schema_prefix}contracts.id"), nullable=False)
    name = Column(String(100), nullable=False)
    conn_str = Column(Text, nullable=False)  # Encrypted connection string
    is_active = Column(Boolean, default=True)

    # Relationships
    contract = relationship("Contract", back_populates="instances")
