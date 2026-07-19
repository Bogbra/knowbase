import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.memory import MemoryScope


class MemoryCreate(BaseModel):
    model_config = ConfigDict(strict=False)

    scope: MemoryScope
    content: str = Field(min_length=1)
    workspace_id: uuid.UUID | None = None
    tags: list[str] = Field(default_factory=list)


class MemoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    workspace_id: uuid.UUID | None
    scope: MemoryScope
    content: str
    tags: list[str]
    metadata_: dict[str, Any]
    created_at: datetime
