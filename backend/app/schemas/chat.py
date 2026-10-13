"""Chat and Messaging Schemas."""
from typing import Optional, List
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    reply: str
    options: Optional[List[str]] = None


class ChatMessageResponse(BaseModel):
    id: int
    user_id: int
    content: str
    username: Optional[str] = "User"
    is_bot: Optional[bool] = False
    timestamp: Optional[str] = None
