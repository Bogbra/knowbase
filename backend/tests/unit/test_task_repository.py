import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models.task import Task, TaskStatus
from app.db.repositories.task_repository import TaskRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def repo(mock_session: AsyncMock) -> TaskRepository:
    return TaskRepository(mock_session)


class TestCreate:
    async def test_creates_task_with_pending_status(
        self, repo: TaskRepository, mock_session: AsyncMock
    ) -> None:
        workspace_id = uuid.uuid4()

        await repo.create(workspace_id, "Build feature X")

        mock_session.add.assert_called_once()
        task = mock_session.add.call_args[0][0]
        assert isinstance(task, Task)
        assert task.workspace_id == workspace_id
        assert task.title == "Build feature X"
        assert task.status == TaskStatus.pending
        assert task.description is None

    async def test_creates_task_with_description(
        self, repo: TaskRepository, mock_session: AsyncMock
    ) -> None:
        await repo.create(uuid.uuid4(), "Deploy to prod", description="Blue-green deployment")

        task = mock_session.add.call_args[0][0]
        assert task.description == "Blue-green deployment"


class TestGetById:
    async def test_returns_task(self, repo: TaskRepository, mock_session: AsyncMock) -> None:
        expected = MagicMock(spec=Task)
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = expected
        mock_session.execute.return_value = execute_result

        result = await repo.get_by_id(uuid.uuid4())

        assert result is expected

    async def test_returns_none_when_missing(
        self, repo: TaskRepository, mock_session: AsyncMock
    ) -> None:
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = execute_result

        result = await repo.get_by_id(uuid.uuid4())

        assert result is None


class TestUpdate:
    async def test_updates_status(self, repo: TaskRepository, mock_session: AsyncMock) -> None:
        task = MagicMock(spec=Task)
        task.title = "Old title"
        task.status = TaskStatus.pending
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = task
        mock_session.execute.return_value = execute_result

        result = await repo.update(uuid.uuid4(), status=TaskStatus.in_progress)

        assert result is task
        assert task.status == TaskStatus.in_progress

    async def test_updates_title_and_assigned_agent(
        self, repo: TaskRepository, mock_session: AsyncMock
    ) -> None:
        task = MagicMock(spec=Task)
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = task
        mock_session.execute.return_value = execute_result

        await repo.update(uuid.uuid4(), title="New title", assigned_agent="planner")

        assert task.title == "New title"
        assert task.assigned_agent == "planner"

    async def test_returns_none_when_task_missing(
        self, repo: TaskRepository, mock_session: AsyncMock
    ) -> None:
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = execute_result

        result = await repo.update(uuid.uuid4(), status=TaskStatus.completed)

        assert result is None


class TestTaskStatusValues:
    def test_all_statuses_have_correct_values(self) -> None:
        assert TaskStatus.pending.value == "pending"
        assert TaskStatus.in_progress.value == "in_progress"
        assert TaskStatus.completed.value == "completed"
        assert TaskStatus.cancelled.value == "cancelled"
        assert TaskStatus.failed.value == "failed"
