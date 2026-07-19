import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_dep
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.models.user import User
from app.db.repositories.agent_repository import AgentRepository
from app.db.repositories.conversation_repository import ConversationRepository
from app.db.repositories.workspace_repository import WorkspaceRepository
from app.schemas.agent import AgentRunRead, ToolCallRead

router = APIRouter(tags=["agent-runs"])


class AgentRunDetailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run: AgentRunRead
    tool_calls: list[ToolCallRead]


def _check_session(db: AsyncSession = Depends(get_db_dep)) -> AsyncSession:
    return db


async def _check_conversation_access(
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    conv_repo = ConversationRepository(db)
    ws_repo = WorkspaceRepository(db)
    conv = await conv_repo.get_by_id(conversation_id)
    if conv is None:
        raise NotFoundError("Conversation", str(conversation_id))
    member = await ws_repo.get_member(conv.workspace_id, user_id)
    if member is None:
        raise ForbiddenError("Not a member of this workspace")


@router.get("/conversations/{conversation_id}/runs", response_model=list[AgentRunRead])
async def list_runs(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_dep),
) -> list[AgentRunRead]:
    await _check_conversation_access(conversation_id, current_user.id, db)
    runs = await AgentRepository(db).get_runs_by_conversation(conversation_id)
    return [AgentRunRead.model_validate(r) for r in runs]


@router.get("/runs/{run_id}", response_model=AgentRunDetailRead)
async def get_run(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_dep),
) -> AgentRunDetailRead:
    repo = AgentRepository(db)
    run = await repo.get_run_by_id(run_id)
    if run is None:
        raise NotFoundError("AgentRun", str(run_id))
    await _check_conversation_access(run.conversation_id, current_user.id, db)
    tool_calls = await repo.get_tool_calls(run_id)
    return AgentRunDetailRead(
        run=AgentRunRead.model_validate(run),
        tool_calls=[ToolCallRead.model_validate(tc) for tc in tool_calls],
    )
