import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.document import DocumentStatus


class DocumentCreate(BaseModel):
    model_config = ConfigDict(strict=False)

    workspace_id: uuid.UUID
    name: str = Field(min_length=1, max_length=500)
    mime_type: str | None = None
    size_bytes: int | None = Field(default=None, ge=0, le=10 * 1024 * 1024)


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    status: DocumentStatus
    s3_key: str | None
    mime_type: str | None
    size_bytes: int | None
    metadata_: dict[str, Any]
    created_at: datetime


class DocumentChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    content: str
    chunk_index: int
    metadata_: dict[str, Any]
