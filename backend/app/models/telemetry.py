from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime, Index
from sqlalchemy.sql import func
from app.db.base import Base
from app.core.config import settings

_schema_args = {"schema": settings.DB_SCHEMA} if "postgresql" in settings.DATABASE_URL and settings.DB_SCHEMA else {}
_schema_prefix = f"{settings.DB_SCHEMA}." if "postgresql" in settings.DATABASE_URL and settings.DB_SCHEMA else ""


class TelemetrySnapshot(Base):
    """Historical telemetry metrics captured periodically for an instance."""
    __tablename__ = "telemetry_snapshots"
    __table_args__ = (
        Index("ix_telemetry_snapshots_instance_captured", "instance_id", "captured_at"),
        _schema_args
    ) if _schema_args else (
        Index("ix_telemetry_snapshots_instance_captured", "instance_id", "captured_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(Integer, ForeignKey(f"{_schema_prefix}instances.id", ondelete="CASCADE"), nullable=True, index=True)
    engine = Column(String(20), default="sqlserver")
    cpu_sql = Column(Float, default=0.0)
    cpu_system = Column(Float, default=0.0)
    active_connections = Column(Integer, default=0)
    total_connections = Column(Integer, default=0)
    blocked_processes = Column(Integer, default=0)
    deadlocks_count = Column(Integer, default=0)
    batch_requests_sec = Column(Float, default=0.0)
    buffer_cache_hit_ratio = Column(Float, nullable=True)
    page_life_expectancy = Column(Integer, nullable=True)
    captured_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class TopQueryHistory(Base):
    """Historical slow and resource-heavy queries captured from DMVs / Query Store."""
    __tablename__ = "top_queries_history"
    __table_args__ = (
        Index("ix_top_queries_instance_captured", "instance_id", "captured_at"),
        _schema_args
    ) if _schema_args else (
        Index("ix_top_queries_instance_captured", "instance_id", "captured_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(Integer, ForeignKey(f"{_schema_prefix}instances.id", ondelete="CASCADE"), nullable=True, index=True)
    engine = Column(String(20), default="sqlserver")
    query_hash = Column(String(64), nullable=True, index=True)
    execution_count = Column(Integer, default=1)
    cpu_total_ms = Column(Float, default=0.0)
    cpu_avg_ms = Column(Float, default=0.0)
    duration_total_ms = Column(Float, default=0.0)
    duration_avg_ms = Column(Float, default=0.0)
    logical_reads = Column(Integer, default=0)
    query_text = Column(Text, nullable=False)
    captured_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
