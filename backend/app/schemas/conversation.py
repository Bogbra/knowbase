import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.conversation import MessageRole


class ConversationCreate(BaseModel):
    model_config = ConfigDict(strict=False)

    workspace_id: uuid.UUID
    title: str = Field(default="New conversation", min_length=1, max_length=500)


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime


class MessageCreate(BaseModel):
    model_config = ConfigDict(strict=False)

    role: MessageRole = MessageRole.user
    content: str = Field(min_length=1)


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: MessageRole
    content: str
    created_at: datetime


class ConversationUpdate(BaseModel):
    model_config = ConfigDict(strict=False)

    title: str = Field(min_length=1, max_length=500)


class MessageSentRead(BaseModel):
    """Returned by POST /conversations/{id}/messages for user-role messages."""

    message: MessageRead
    run_id: uuid.UUID | None = None
