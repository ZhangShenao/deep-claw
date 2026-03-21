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


class EmailAccountOut(BaseModel):
    id: uuid.UUID
    email_address: str
    provider_label: str
    imap_host: str
    imap_port: int
    imap_security: str
    auth_type: str
    poll_interval_minutes: int
    enabled: bool
    last_check_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EmailAccountCreate(BaseModel):
    email_address: str = Field(..., min_length=3, max_length=320)
    provider_label: str = Field(default="", max_length=120)
    imap_host: str = Field(..., min_length=1, max_length=255)
    imap_port: int = Field(default=993, ge=1, le=65535)
    imap_security: str = Field(default="ssl_tls", max_length=32)
    auth_type: str = Field(default="app_password", max_length=32)
    credential: str = Field(..., min_length=1, max_length=4000)
    poll_interval_minutes: int = Field(default=15, ge=5, le=1440)
    enabled: bool = True


class NotificationOut(BaseModel):
    id: uuid.UUID
    type: str
    account_id: uuid.UUID | None
    digest_id: uuid.UUID | None
    title: str
    body: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}
