"""Chat Repository."""
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.chat import ChatMessage
from app.models.user import User
from app.core.security import get_password_hash


def get_chat_history(db: Session) -> List[Dict[str, Any]]:
    """Return all chat messages ordered chronologically."""
    messages = db.query(ChatMessage).order_by(ChatMessage.timestamp).all()
    return [
        {
            "id": msg.id,
            "user_id": msg.user_id,
            "content": msg.content,
            "timestamp": str(msg.timestamp) if msg.timestamp else None,
        }
        for msg in messages
    ]


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
