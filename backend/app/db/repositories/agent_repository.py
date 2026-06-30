import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent import AgentRun, AgentRunStatus, ToolCall, ToolCallStatus


class AgentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_run_by_id(self, run_id: uuid.UUID) -> AgentRun | None:
        result = await self._session.execute(select(AgentRun).where(AgentRun.id == run_id))
        return result.scalar_one_or_none()

    async def get_runs_by_conversation(self, conversation_id: uuid.UUID) -> list[AgentRun]:
        result = await self._session.execute(
            select(AgentRun)
            .where(AgentRun.conversation_id == conversation_id)
            .order_by(AgentRun.started_at.desc())
        )
        return list(result.scalars().all())

    async def create_run(
        self,
        conversation_id: uuid.UUID,
        message_id: uuid.UUID | None = None,
    ) -> AgentRun:
        run = AgentRun(
            conversation_id=conversation_id,
            message_id=message_id,
            graph_state={},
            status=AgentRunStatus.running,
        )
        self._session.add(run)
        await self._session.flush()
        await self._session.refresh(run)
        return run

    async def update_run(
        self,
        run_id: uuid.UUID,
        status: AgentRunStatus,
        graph_state: dict[str, Any] | None = None,
    ) -> AgentRun | None:
        run = await self.get_run_by_id(run_id)
        if run is None:
            return None
        run.status = status
        if graph_state is not None:
            run.graph_state = graph_state
        if status in (AgentRunStatus.completed, AgentRunStatus.failed):
            run.finished_at = datetime.now(UTC)
        await self._session.flush()
        return run

    async def create_tool_call(
        self,
        agent_run_id: uuid.UUID,
        tool_name: str,
        input_data: dict[str, Any],
    ) -> ToolCall:
        call = ToolCall(
            agent_run_id=agent_run_id,
            tool_name=tool_name,
            input_data=input_data,
            output_data=None,
            status=ToolCallStatus.ok,
        )
        self._session.add(call)
        await self._session.flush()
        await self._session.refresh(call)
        return call

    async def update_tool_call(
        self,
        tool_call_id: uuid.UUID,
        output_data: dict[str, Any],
        status: ToolCallStatus,
        duration_ms: int | None = None,
    ) -> ToolCall | None:
        result = await self._session.execute(select(ToolCall).where(ToolCall.id == tool_call_id))
        call = result.scalar_one_or_none()
        if call is None:
            return None
        call.output_data = output_data
        call.status = status
        call.duration_ms = duration_ms
        await self._session.flush()
        return call

    async def get_tool_calls(self, agent_run_id: uuid.UUID) -> list[ToolCall]:
        result = await self._session.execute(
            select(ToolCall)
            .where(ToolCall.agent_run_id == agent_run_id)
            .order_by(ToolCall.called_at.asc())
        )
        return list(result.scalars().all())
