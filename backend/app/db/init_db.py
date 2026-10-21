"""Database initialization and seeding module."""
import logging
from sqlalchemy import text, inspect
from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import engine, SessionLocal
from app.models import Base, User


def create_tables() -> None:
    """Create schemas and tables defined in models."""
    try:
        # If using PostgreSQL with schema, ensure schema exists first
        if "postgresql" in settings.DATABASE_URL and settings.DB_SCHEMA:
            with engine.connect() as conn:
                conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.DB_SCHEMA}"))
                conn.commit()

        Base.metadata.create_all(bind=engine)
        ensure_user_privacy_columns()
        logging.info("Database tables initialized successfully.")

        # Seed default admin and maintenance state
        db = SessionLocal()
        try:
            seed_default_admin(db)
            seed_system_maintenance(db)
            seed_telemetry_baseline(db)
        finally:
            db.close()
    except Exception as exc:
        logging.error(f"Error during create_tables: {exc}")
        logging.warning("FastAPI will start, but database access may be limited until DB is ready.")


def ensure_user_privacy_columns() -> None:
    """Add privacy columns to an existing users table (idempotent, no Alembic in project)."""
    schema = settings.DB_SCHEMA if "postgresql" in settings.DATABASE_URL and settings.DB_SCHEMA else None
    insp = inspect(engine)
    if not insp.has_table("users", schema=schema):
        return
    existing = {c["name"] for c in insp.get_columns("users", schema=schema)}
    is_pg = "postgresql" in settings.DATABASE_URL
    table = f"{schema}.users" if schema else "users"
    ts_type = "TIMESTAMP WITH TIME ZONE" if is_pg else "DATETIME"
    bool_default = "BOOLEAN NOT NULL DEFAULT FALSE" if is_pg else "BOOLEAN NOT NULL DEFAULT 0"
    wanted = {
        "consent_version": "VARCHAR(20)",
        "consent_accepted_at": ts_type,
        "email_opt_out": bool_default,
        "email_opt_out_at": ts_type,
    }
    with engine.connect() as conn:
        for name, ddl in wanted.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
                logging.info(f"Migración: columna users.{name} agregada.")
        conn.commit()


def seed_default_admin(session) -> None:
    """Seed default administrator user if none exists."""
    admin = session.query(User).filter_by(username=settings.ADMIN_DEFAULT_USERNAME).first()
    if not admin:
        new_admin = User(
            username=settings.ADMIN_DEFAULT_USERNAME,
            full_name="Administrator",
            hashed_password=get_password_hash(settings.ADMIN_DEFAULT_PASSWORD),
            role="Administrador",
            mfa_enabled=False,
        )
        session.add(new_admin)
        session.commit()
        logging.info(f"Default admin created ({settings.ADMIN_DEFAULT_USERNAME})")


def seed_system_maintenance(session) -> None:
    """Ensure system maintenance record exists."""
    from app.models.system_maintenance import SystemMaintenance
    maint = session.query(SystemMaintenance).first()
    if not maint:
        new_maint = SystemMaintenance(
            is_active=False,
            title="Ajustes del Sistema en Progreso",
            subtitle="Optimizando motores de bases de datos, reindexando y aplicando configuraciones DBA...",
            disabled_modules="[]"
        )
        session.add(new_maint)
        session.commit()
        logging.info("Default system maintenance record initialized in database.")


def seed_telemetry_baseline(session) -> None:
    """Seed initial 24h baseline snapshots if database table is empty."""
    import random
    from datetime import datetime, timedelta, timezone
    from app.models.telemetry import TelemetrySnapshot

    count = session.query(TelemetrySnapshot).count()
    if count == 0:
        now = datetime.now(timezone.utc)
        snapshots = []
        for i in range(24, 0, -1):
            ts = now - timedelta(hours=i)
            # Realistic baseline metrics
            cpu_val = round(max(3.0, min(85.0, 18.0 + random.uniform(-8.0, 15.0) + (15.0 if 9 <= ts.hour <= 18 else 0.0))), 1)
            blocked_val = 1 if (ts.hour in (1, 8, 14) and random.random() > 0.4) else 0
            deadlock_val = 1 if (ts.hour == 8 and random.random() > 0.7) else 0
            throughput = round(random.uniform(220.0, 530.0), 1)

            snapshots.append(TelemetrySnapshot(
                engine="sqlserver",
                cpu_sql=cpu_val,
                cpu_system=round(cpu_val + random.uniform(2.0, 6.0), 1),
                active_connections=random.randint(4, 28),
                total_connections=random.randint(30, 85),
                blocked_processes=blocked_val,
                deadlocks_count=deadlock_val,
                batch_requests_sec=throughput,
                buffer_cache_hit_ratio=round(random.uniform(98.5, 99.9), 2),
                page_life_expectancy=random.randint(1800, 4200),
                captured_at=ts
            ))
        session.bulk_save_objects(snapshots)
        session.commit()
        logging.info("Historical telemetry 24h baseline initialized in database.")

