import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

import sqlalchemy as sa
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AgentRunStatus(StrEnum):
    running = "running"
    completed = "completed"
    failed = "failed"


class ToolCallStatus(StrEnum):
    ok = "ok"
    error = "error"


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    graph_state: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
    )
    status: Mapped[AgentRunStatus] = mapped_column(
        Enum(AgentRunStatus, name="agentrunstatus"),
        nullable=False,
        default=AgentRunStatus.running,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    input_data: Mapped[dict[str, Any]] = mapped_column(
        "input", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
    )
    output_data: Mapped[dict[str, Any] | None] = mapped_column("output", JSONB, nullable=True)
    status: Mapped[ToolCallStatus] = mapped_column(
        Enum(ToolCallStatus, name="toolcallstatus"),
        nullable=False,
        default=ToolCallStatus.ok,
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    called_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
