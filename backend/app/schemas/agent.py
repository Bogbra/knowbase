import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.db.models.agent import AgentRunStatus, ToolCallStatus


class AgentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    message_id: uuid.UUID | None
    status: AgentRunStatus
    started_at: datetime
    finished_at: datetime | None


class ToolCallRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_run_id: uuid.UUID
    tool_name: str
    input_data: dict[str, Any]
    output_data: dict[str, Any] | None
    status: ToolCallStatus
    duration_ms: int | None
    called_at: datetime
