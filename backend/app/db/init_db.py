"""Database initialization and seeding module."""
import logging
from sqlalchemy import text
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
