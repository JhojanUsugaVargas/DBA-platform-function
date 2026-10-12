"""User Repository."""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.user import User


def get_by_username(db: Session, username: str) -> Optional[User]:
    """Find a user by username."""
    return db.query(User).filter(User.username == username).first()


def get_by_id(db: Session, user_id: int) -> Optional[User]:
    """Find a user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def list_users(db: Session) -> List[User]:
    """List all users."""
    return db.query(User).all()


def create_user(db: Session, username: str, full_name: str, hashed_password: str, role: str) -> User:
    """Create a new user."""
    user = User(
        username=username,
        full_name=full_name,
        hashed_password=hashed_password,
        role=role,
        mfa_enabled=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User) -> None:
    """Delete a user."""
    db.delete(user)
    db.commit()
