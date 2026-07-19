import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiKeyCreate(BaseModel):
    model_config = ConfigDict(strict=False)

    name: str = Field(min_length=1, max_length=255)
    workspace_id: uuid.UUID


class ApiKeyCreated(BaseModel):
    """Returned once on creation — the raw key is never stored and cannot be retrieved again."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    workspace_id: uuid.UUID
    created_at: datetime
    key: str  # raw key, shown exactly once


class ApiKeyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    workspace_id: uuid.UUID
    created_at: datetime
    last_used_at: datetime | None = None


class SearchRequest(BaseModel):
    model_config = ConfigDict(strict=False)

    query: str = Field(min_length=1, max_length=2000)
    k: int = Field(default=8, ge=1, le=20)


class ChunkResult(BaseModel):
    document_id: str
    document_name: str
    chapter: str
    content: str
    distance: float
    source_label: str  # "{document_name}, {chapter}" or "{document_name}"


class SearchResponse(BaseModel):
    chunks: list[ChunkResult]
    query: str
    total: int
