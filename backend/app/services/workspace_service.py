import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.models.workspace import Workspace, WorkspaceMember, WorkspaceMemberRole
from app.db.repositories.workspace_repository import WorkspaceRepository


class WorkspaceService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = WorkspaceRepository(session)

    async def create(self, owner_id: uuid.UUID, name: str) -> Workspace:
        workspace = await self._repo.create(name=name, owner_id=owner_id)
        await self._repo.add_member(workspace.id, owner_id, WorkspaceMemberRole.owner)
        return workspace

    async def list_for_user(self, user_id: uuid.UUID) -> list[Workspace]:
        return await self._repo.get_for_user(user_id)

    async def get(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> tuple[Workspace, WorkspaceMember]:
        workspace = await self._repo.get_by_id(workspace_id)
        if workspace is None:
            raise NotFoundError("Workspace", str(workspace_id))
        member = await self._repo.get_member(workspace_id, user_id)
        if member is None:
            raise ForbiddenError("Not a member of this workspace")
        return workspace, member

    async def add_member(
        self,
        workspace_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        target_user_id: uuid.UUID,
        role: WorkspaceMemberRole,
    ) -> WorkspaceMember:
        _, member = await self.get(workspace_id, requesting_user_id)
        if member.role not in (WorkspaceMemberRole.owner, WorkspaceMemberRole.editor):
            raise ForbiddenError("Only workspace owners or editors can add members")
        existing = await self._repo.get_member(workspace_id, target_user_id)
        if existing is not None:
            raise ForbiddenError("User is already a member of this workspace")
        return await self._repo.add_member(workspace_id, target_user_id, role)

    async def remove_member(
        self,
        workspace_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        target_user_id: uuid.UUID,
    ) -> None:
        _, member = await self.get(workspace_id, requesting_user_id)
        if member.role != WorkspaceMemberRole.owner:
            raise ForbiddenError("Only workspace owners can remove members")
        if requesting_user_id == target_user_id:
            raise ForbiddenError("Workspace owner cannot remove themselves")
        target = await self._repo.get_member(workspace_id, target_user_id)
        if target is None:
            raise NotFoundError("Member", str(target_user_id))
        from sqlalchemy import delete

        from app.db.models.workspace import WorkspaceMember

        await self._repo._session.execute(
            delete(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == target_user_id,
            )
        )

    async def list_members(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[WorkspaceMember]:
        await self.get(workspace_id, user_id)
        return await self._repo.get_members(workspace_id)
