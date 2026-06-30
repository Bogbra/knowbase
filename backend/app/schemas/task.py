import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.task import TaskStatus


class TaskCreate(BaseModel):
    model_config = ConfigDict(strict=False)

    workspace_id: uuid.UUID
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None


class TaskUpdate(BaseModel):
    model_config = ConfigDict(strict=False)

    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    status: TaskStatus | None = None
    assigned_agent: str | None = None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    description: str | None
    status: TaskStatus
    assigned_agent: str | None
    created_at: datetime
    updated_at: datetime | None
