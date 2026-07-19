"""Pydantic schemas for account self-service: deletion and data export."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DeleteAccountRequest(BaseModel):
    model_config = ConfigDict(strict=False)

    password: str


class ExportProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: str
    created_at: datetime
    # hashed_password and is_active intentionally excluded


class ExportWorkspace(BaseModel):
    id: uuid.UUID
    name: str
    role: str


class ExportMessage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    created_at: datetime


class ExportConversation(BaseModel):
    id: uuid.UUID
    title: str
    workspace_id: uuid.UUID
    created_at: datetime
    messages: list[ExportMessage]


class ExportMemory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scope: str
    content: str
    workspace_id: uuid.UUID | None
    tags: list[str]
    created_at: datetime


class ExportDocument(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    status: str
    mime_type: str | None
    size_bytes: int | None
    created_at: datetime
    # s3_key intentionally excluded — internal storage path


class ExportApiKey(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    workspace_id: uuid.UUID
    created_at: datetime
    last_used_at: datetime | None = None
    # key_hash intentionally excluded — never expose stored hashes


class ExportResponse(BaseModel):
    exported_at: datetime
    profile: ExportProfile
    workspaces: list[ExportWorkspace]
    conversations: list[ExportConversation]
    memories: list[ExportMemory]
    documents: list[ExportDocument]
    api_keys: list[ExportApiKey]
