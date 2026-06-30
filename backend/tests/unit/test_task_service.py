import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.models.task import Task, TaskStatus
from app.db.models.workspace import Workspace, WorkspaceMember, WorkspaceMemberRole
from app.services.task_service import TaskService


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(mock_session: AsyncMock) -> TaskService:
    return TaskService(mock_session)


def _mock_task(workspace_id: uuid.UUID | None = None) -> MagicMock:
    task = MagicMock(spec=Task)
    task.id = uuid.uuid4()
    task.workspace_id = workspace_id or uuid.uuid4()
    task.status = TaskStatus.pending
    return task


def _mock_workspace() -> MagicMock:
    ws = MagicMock(spec=Workspace)
    ws.id = uuid.uuid4()
    return ws


def _mock_member() -> MagicMock:
    m = MagicMock(spec=WorkspaceMember)
    m.role = WorkspaceMemberRole.editor
    return m


class TestCreate:
    async def test_raises_not_found_when_workspace_missing(self, service: TaskService) -> None:
        service._ws_repo.get_by_id = AsyncMock(return_value=None)  # type: ignore[method-assign]

        with pytest.raises(NotFoundError):
            await service.create(uuid.uuid4(), uuid.uuid4(), "Task 1")

    async def test_raises_forbidden_when_not_member(self, service: TaskService) -> None:
        service._ws_repo.get_by_id = AsyncMock(return_value=_mock_workspace())  # type: ignore[method-assign]
        service._ws_repo.get_member = AsyncMock(return_value=None)  # type: ignore[method-assign]

        with pytest.raises(ForbiddenError):
            await service.create(uuid.uuid4(), uuid.uuid4(), "Task 1")

    async def test_creates_task_when_member(self, service: TaskService) -> None:
        workspace_id = uuid.uuid4()
        user_id = uuid.uuid4()
        task = _mock_task(workspace_id)

        service._ws_repo.get_by_id = AsyncMock(return_value=_mock_workspace())  # type: ignore[method-assign]
        service._ws_repo.get_member = AsyncMock(return_value=_mock_member())  # type: ignore[method-assign]
        service._task_repo.create = AsyncMock(return_value=task)  # type: ignore[method-assign]

        result = await service.create(workspace_id, user_id, "Build API")

        service._task_repo.create.assert_awaited_once_with(workspace_id, "Build API", None)
        assert result is task


class TestGet:
    async def test_raises_not_found_when_task_missing(self, service: TaskService) -> None:
        service._task_repo.get_by_id = AsyncMock(return_value=None)  # type: ignore[method-assign]

        with pytest.raises(NotFoundError):
            await service.get(uuid.uuid4(), uuid.uuid4())

    async def test_returns_task_for_workspace_member(self, service: TaskService) -> None:
        workspace_id = uuid.uuid4()
        task = _mock_task(workspace_id)

        service._task_repo.get_by_id = AsyncMock(return_value=task)  # type: ignore[method-assign]
        service._ws_repo.get_by_id = AsyncMock(return_value=_mock_workspace())  # type: ignore[method-assign]
        service._ws_repo.get_member = AsyncMock(return_value=_mock_member())  # type: ignore[method-assign]

        result = await service.get(task.id, uuid.uuid4())

        assert result is task


class TestUpdate:
    async def test_updates_task_status(self, service: TaskService) -> None:
        workspace_id = uuid.uuid4()
        task = _mock_task(workspace_id)
        updated = _mock_task(workspace_id)
        updated.status = TaskStatus.completed

        service._task_repo.get_by_id = AsyncMock(return_value=task)  # type: ignore[method-assign]
        service._ws_repo.get_by_id = AsyncMock(return_value=_mock_workspace())  # type: ignore[method-assign]
        service._ws_repo.get_member = AsyncMock(return_value=_mock_member())  # type: ignore[method-assign]
        service._task_repo.update = AsyncMock(return_value=updated)  # type: ignore[method-assign]

        result = await service.update(task.id, uuid.uuid4(), status=TaskStatus.completed)

        assert result is updated
        service._task_repo.update.assert_awaited_once_with(
            task.id,
            title=None,
            description=None,
            status=TaskStatus.completed,
            assigned_agent=None,
        )
