"""Application Configuration Module.

Reads environment variables and provides structured settings for the DataCheck API.
"""
from pathlib import Path
import os
from typing import List
from dotenv import load_dotenv

# Search for .env in project root or current working dir
_root_env = Path(__file__).resolve().parents[3] / ".env"
_backend_env = Path(__file__).resolve().parents[2] / ".env"

if _root_env.exists():
    load_dotenv(_root_env)
elif _backend_env.exists():
    load_dotenv(_backend_env)
else:
    load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    APP_NAME: str = os.getenv("APP_NAME", "DataCheck API")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

    # Security & JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "datacheck-insecure-secret-key-change-me")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    # Fernet symmetric encryption key for remote connection strings
    FERNET_KEY: str = os.getenv(
        "FERNET_KEY",
        "u275j75GZ7XN9Lh3t_tL05iZz-5hO7pY-o28pZkU7_o="
    )

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+pg8000://postgres:postgres@localhost:5432/dba_platform_function"
    )
    DB_SCHEMA: str = os.getenv("DB_SCHEMA", "datacheck")

    # AI / External services
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # SMTP for OTP notifications
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    OTP_EXPIRE_SECONDS: int = int(os.getenv("OTP_EXPIRE_SECONDS", "120"))

    # Admin seed defaults
    ADMIN_DEFAULT_USERNAME: str = os.getenv("ADMIN_DEFAULT_USERNAME", "admin")
    ADMIN_DEFAULT_PASSWORD: str = os.getenv("ADMIN_DEFAULT_PASSWORD", "Admin123!")

    # Privacy / legal (Ley 1581 de 2012 - Habeas Data)
    DATA_CONTROLLER_NAME: str = os.getenv("DATA_CONTROLLER_NAME", "Equipo DBA - DataCheck Pro")
    PRIVACY_CONTACT_EMAIL: str = os.getenv("PRIVACY_CONTACT_EMAIL", "privacidad@datacheck.local")
    LEGAL_VERSION: str = os.getenv("LEGAL_VERSION", "2026-10-20")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:4200")
    PUBLIC_API_URL: str = os.getenv("PUBLIC_API_URL", "http://localhost:8005")
    UNSUBSCRIBE_TOKEN_EXPIRE_DAYS: int = int(os.getenv("UNSUBSCRIBE_TOKEN_EXPIRE_DAYS", "365"))

    # CORS
    _cors_raw: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:4200,http://127.0.0.1:4200,http://localhost:8005,http://127.0.0.1:8005"
    )

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self._cors_raw.split(",") if origin.strip()]


settings = Settings()
