import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.task import Task, TaskStatus


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, task_id: uuid.UUID) -> Task | None:
        result = await self._session.execute(select(Task).where(Task.id == task_id))
        return result.scalar_one_or_none()

    async def get_by_workspace(self, workspace_id: uuid.UUID) -> list[Task]:
        result = await self._session.execute(
            select(Task).where(Task.workspace_id == workspace_id).order_by(Task.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_status(self, workspace_id: uuid.UUID, status: TaskStatus) -> list[Task]:
        result = await self._session.execute(
            select(Task)
            .where(Task.workspace_id == workspace_id, Task.status == status)
            .order_by(Task.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(
        self,
        workspace_id: uuid.UUID,
        title: str,
        description: str | None = None,
    ) -> Task:
        task = Task(
            workspace_id=workspace_id,
            title=title,
            description=description,
            status=TaskStatus.pending,
        )
        self._session.add(task)
        await self._session.flush()
        await self._session.refresh(task)
        return task

    async def update(
        self,
        task_id: uuid.UUID,
        title: str | None = None,
        description: str | None = None,
        status: TaskStatus | None = None,
        assigned_agent: str | None = None,
    ) -> Task | None:
        task = await self.get_by_id(task_id)
        if task is None:
            return None
        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if status is not None:
            task.status = status
        if assigned_agent is not None:
            task.assigned_agent = assigned_agent
        await self._session.flush()
        return task
