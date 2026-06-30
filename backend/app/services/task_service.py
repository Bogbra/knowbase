import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.models.task import Task, TaskStatus
from app.db.repositories.task_repository import TaskRepository
from app.db.repositories.workspace_repository import WorkspaceRepository


class TaskService:
    def __init__(self, session: AsyncSession) -> None:
        self._task_repo = TaskRepository(session)
        self._ws_repo = WorkspaceRepository(session)

    async def _check_workspace_access(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> None:
        workspace = await self._ws_repo.get_by_id(workspace_id)
        if workspace is None:
            raise NotFoundError("Workspace", str(workspace_id))
        member = await self._ws_repo.get_member(workspace_id, user_id)
        if member is None:
            raise ForbiddenError("Not a member of this workspace")

    async def create(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str,
        description: str | None = None,
    ) -> Task:
        await self._check_workspace_access(workspace_id, user_id)
        return await self._task_repo.create(workspace_id, title, description)

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        status: TaskStatus | None = None,
    ) -> list[Task]:
        await self._check_workspace_access(workspace_id, user_id)
        if status is not None:
            return await self._task_repo.get_by_status(workspace_id, status)
        return await self._task_repo.get_by_workspace(workspace_id)

    async def get(self, task_id: uuid.UUID, user_id: uuid.UUID) -> Task:
        task = await self._task_repo.get_by_id(task_id)
        if task is None:
            raise NotFoundError("Task", str(task_id))
        await self._check_workspace_access(task.workspace_id, user_id)
        return task

    async def update(
        self,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str | None = None,
        description: str | None = None,
        status: TaskStatus | None = None,
        assigned_agent: str | None = None,
    ) -> Task:
        task = await self.get(task_id, user_id)
        updated = await self._task_repo.update(
            task.id,
            title=title,
            description=description,
            status=status,
            assigned_agent=assigned_agent,
        )
        return updated or task

    async def delete(self, task_id: uuid.UUID, user_id: uuid.UUID) -> None:
        task = await self.get(task_id, user_id)
        await self._task_repo._session.delete(task)
