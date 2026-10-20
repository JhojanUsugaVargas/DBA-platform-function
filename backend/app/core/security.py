"""Security utilities module.

Handles password hashing, JWT token generation/validation,
and symmetric encryption for sensitive connection strings.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Fernet cipher instance initialized with configured key
try:
    _fernet_cipher = Fernet(settings.FERNET_KEY.encode() if isinstance(settings.FERNET_KEY, str) else settings.FERNET_KEY)
except Exception:
    # Fallback to standard 32-byte url-safe base64 key if key was invalid
    _fernet_cipher = Fernet(b"u275j75GZ7XN9Lh3t_tL05iZz-5hO7pY-o28pZkU7_o=")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hashed representation."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate a bcrypt hash from a plaintext password."""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # Unsubscribe tokens must never be accepted as session tokens
        if payload.get("purpose"):
            return {}
        return payload
    except jwt.PyJWTError:
        return {}


def create_unsubscribe_token(username: str) -> str:
    """Signed, purpose-bound token used in the email opt-out link."""
    return create_access_token(
        {"sub": username, "purpose": "unsubscribe"},
        expires_delta=timedelta(days=settings.UNSUBSCRIBE_TOKEN_EXPIRE_DAYS),
    )


def decode_unsubscribe_token(token: str) -> Optional[str]:
    """Return username if token is a valid unsubscribe token, else None."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("purpose") != "unsubscribe":
        return None
    return payload.get("sub")


def encrypt_data(data: str) -> str:
    """Encrypt a string with Fernet."""
    if not data:
        return data
    return _fernet_cipher.encrypt(data.encode()).decode()


def decrypt_data(data: str) -> str:
    """Decrypt a Fernet encrypted string with graceful plaintext fallback."""
    if not data:
        return data
    try:
        return _fernet_cipher.decrypt(data.encode()).decode()
    except Exception:
        # If decryption fails (e.g., legacy plaintext in DB or different key), return original
        return data
