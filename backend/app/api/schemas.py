import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ConversationOut(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=500)


class ChatStreamIn(BaseModel):
    thread_id: uuid.UUID
    message: str = Field(..., min_length=1, max_length=32000)
