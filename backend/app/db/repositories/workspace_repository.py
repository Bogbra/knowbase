import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.workspace import Workspace, WorkspaceMember, WorkspaceMemberRole


class WorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, workspace_id: uuid.UUID) -> Workspace | None:
        result = await self._session.execute(select(Workspace).where(Workspace.id == workspace_id))
        return result.scalar_one_or_none()

    async def get_by_owner(self, owner_id: uuid.UUID) -> list[Workspace]:
        result = await self._session.execute(
            select(Workspace).where(Workspace.owner_id == owner_id)
        )
        return list(result.scalars().all())

    async def get_for_user(self, user_id: uuid.UUID) -> list[Workspace]:
        result = await self._session.execute(
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
        )
        return list(result.scalars().all())

    async def create(self, name: str, owner_id: uuid.UUID) -> Workspace:
        workspace = Workspace(name=name, owner_id=owner_id)
        self._session.add(workspace)
        await self._session.flush()
        await self._session.refresh(workspace)
        return workspace

    async def get_member(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkspaceMember | None:
        result = await self._session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def add_member(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        role: WorkspaceMemberRole = WorkspaceMemberRole.viewer,
    ) -> WorkspaceMember:
        member = WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role=role)
        self._session.add(member)
        await self._session.flush()
        await self._session.refresh(member)
        return member

    async def get_memberships_for_user(self, user_id: uuid.UUID) -> list[WorkspaceMember]:
        result = await self._session.execute(
            select(WorkspaceMember).where(WorkspaceMember.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_members(self, workspace_id: uuid.UUID) -> list[WorkspaceMember]:
        result = await self._session.execute(
            select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id)
        )
        return list(result.scalars().all())
