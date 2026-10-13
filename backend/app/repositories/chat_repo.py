"""Chat Repository."""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.chat import ChatMessage
from app.models.user import User
from app.core.security import get_password_hash


def get_chat_history(db: Session, limit: int = 100) -> List[Dict[str, Any]]:
    """Return all chat messages ordered chronologically with user metadata."""
    messages = db.query(ChatMessage).order_by(ChatMessage.timestamp).limit(limit).all()
    results = []
    for msg in messages:
        uname = msg.user.username if msg.user else "User"
        is_bot = (uname == "AI_DBA")
        results.append({
            "id": msg.id,
            "user_id": msg.user_id,
            "username": uname,
            "is_bot": is_bot,
            "content": msg.content,
            "timestamp": str(msg.timestamp) if msg.timestamp else None,
        })
    return results


def add_chat_message(db: Session, username: str, content: str) -> int:
    """Create a chat message for the given user, auto-creating AI bot if needed."""
    user = db.query(User).filter(User.username == username).first()

    if not user and username == "AI_DBA":
        user = User(
            username="AI_DBA",
            full_name="DataCheck AI",
            hashed_password=get_password_hash("bot-secure-password-123!"),
            role="bot",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    if not user:
        raise ValueError(f"Usuario no encontrado: {username}")

    message = ChatMessage(user_id=user.id, content=content)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message.id


def clear_chat_history(db: Session, user_id: Optional[int] = None) -> int:
    """Deletes chat messages from the history."""
    query = db.query(ChatMessage)
    deleted_count = query.delete(synchronize_session=False)
    db.commit()
    return deleted_count
