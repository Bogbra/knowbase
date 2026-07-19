import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_dep
from app.core.exceptions import NotFoundError
from app.db.models.user import User
from app.db.repositories.memory_repository import MemoryRepository
from app.db.repositories.user_repository import UserRepository
from app.schemas.memory import MemoryRead
from app.schemas.workspace import (
    MemberInviteByEmail,
    WorkspaceCreate,
    WorkspaceMemberCreate,
    WorkspaceMemberRead,
    WorkspaceRead,
)
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _service(db: AsyncSession = Depends(get_db_dep)) -> WorkspaceService:
    return WorkspaceService(db)


@router.post("", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    body: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(_service),
) -> WorkspaceRead:
    workspace = await service.create(current_user.id, body.name)
    return WorkspaceRead.model_validate(workspace)


@router.get("", response_model=list[WorkspaceRead])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(_service),
) -> list[WorkspaceRead]:
    workspaces = await service.list_for_user(current_user.id)
    return [WorkspaceRead.model_validate(w) for w in workspaces]


@router.get("/{workspace_id}", response_model=WorkspaceRead)
async def get_workspace(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(_service),
) -> WorkspaceRead:
    workspace, _ = await service.get(workspace_id, current_user.id)
    return WorkspaceRead.model_validate(workspace)


@router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberRead])
async def list_members(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(_service),
    db: AsyncSession = Depends(get_db_dep),
) -> list[WorkspaceMemberRead]:
    members = await service.list_members(workspace_id, current_user.id)
    user_repo = UserRepository(db)
    result: list[WorkspaceMemberRead] = []
    for m in members:
        user = await user_repo.get_by_id(m.user_id)
        r = WorkspaceMemberRead.model_validate(m)
        r.user_email = user.email if user else None
        result.append(r)
    return result


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    workspace_id: uuid.UUID,
    body: WorkspaceMemberCreate,
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(_service),
) -> WorkspaceMemberRead:
    member = await service.add_member(workspace_id, current_user.id, body.user_id, body.role)
    return WorkspaceMemberRead.model_validate(member)


@router.post(
    "/{workspace_id}/members/invite",
    response_model=WorkspaceMemberRead,
    status_code=status.HTTP_201_CREATED,
)
async def invite_member_by_email(
    workspace_id: uuid.UUID,
    body: MemberInviteByEmail,
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(_service),
    db: AsyncSession = Depends(get_db_dep),
) -> WorkspaceMemberRead:
    user_repo = UserRepository(db)
    target = await user_repo.get_by_email(body.email)
    if target is None:
        raise NotFoundError("User", body.email)
    member = await service.add_member(workspace_id, current_user.id, target.id, body.role)
    r = WorkspaceMemberRead.model_validate(member)
    r.user_email = target.email
    return r


@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(_service),
) -> None:
    await service.remove_member(workspace_id, current_user.id, user_id)


@router.get("/{workspace_id}/memories", response_model=list[MemoryRead])
async def list_workspace_memories(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(_service),
    db: AsyncSession = Depends(get_db_dep),
) -> list[MemoryRead]:
    """List all memories scoped to this workspace.

    Requires workspace membership. Any member role (owner / editor / viewer) may
    view memories. Use DELETE /memories/{id} to remove individual entries.
    """
    await service.get(workspace_id, current_user.id)  # membership check
    memories = await MemoryRepository(db).get_by_workspace(workspace_id)
    return [MemoryRead.model_validate(m) for m in memories]
