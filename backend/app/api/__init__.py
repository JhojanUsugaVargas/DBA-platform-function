"""API routers package."""
from app.api.auth import router as auth_router
from app.api.admin import router as admin_router
from app.api.dba import router as dba_router
from app.api.chat import router as chat_router
from app.api.feedback import router as feedback_router

__all__ = [
    "auth_router",
    "admin_router",
    "dba_router",
    "chat_router",
    "feedback_router",
]
