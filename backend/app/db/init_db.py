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

        # Seed default admin
        db = SessionLocal()
        try:
            seed_default_admin(db)
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
