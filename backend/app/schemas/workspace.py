import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.workspace import WorkspaceMemberRole


class WorkspaceCreate(BaseModel):
    model_config = ConfigDict(strict=False)

    name: str = Field(min_length=1, max_length=255)


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    created_at: datetime


class WorkspaceMemberCreate(BaseModel):
    model_config = ConfigDict(strict=False)

    user_id: uuid.UUID
    role: WorkspaceMemberRole = WorkspaceMemberRole.viewer


class MemberInviteByEmail(BaseModel):
    model_config = ConfigDict(strict=False)

    email: str
    role: WorkspaceMemberRole = WorkspaceMemberRole.viewer


class WorkspaceMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    role: WorkspaceMemberRole
    joined_at: datetime
    user_email: str | None = None
