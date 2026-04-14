from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class ChatSessionCreateResponse(BaseModel):
    session_id: str


class ChatMessageCreate(BaseModel):
    session_id: str | None = None
    message: str = Field(..., min_length=1, max_length=8000)


class ChatTurnResponse(BaseModel):
    session_id: str
    reply: str
    messages: list[ChatMessage]