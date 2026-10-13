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


def create_user(
    db: Session,
    username: str,
    full_name: Optional[str],
    hashed_password: str,
    role: str,
    email: Optional[str] = None
) -> User:
    """Create a new user with optional email and full name."""
    user = User(
        username=username,
        full_name=full_name or username,
        email=email,
        hashed_password=hashed_password,
        role=role,
        mfa_enabled=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_password(db: Session, user_id: int, new_hashed_password: str) -> Optional[User]:
    """Update password for a given user ID."""
    user = get_by_id(db, user_id)
    if not user:
        return None
    user.hashed_password = new_hashed_password
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User) -> None:
    """Delete a user."""
    db.delete(user)
    db.commit()


def update_user_details(
    db: Session,
    user_id: int,
    full_name: Optional[str] = None,
    email: Optional[str] = None,
    role: Optional[str] = None
) -> Optional[User]:
    """Update profile/role details for a given user ID."""
    user = get_by_id(db, user_id)
    if not user:
        return None
    if full_name is not None:
        user.full_name = full_name
    if email is not None:
        user.email = email
    if role is not None:
        user.role = role
    db.commit()
    db.refresh(user)
    return user
