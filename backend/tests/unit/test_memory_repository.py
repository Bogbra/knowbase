import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models.memory import Memory, MemoryScope
from app.db.repositories.memory_repository import MemoryRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def repo(mock_session: AsyncMock) -> MemoryRepository:
    return MemoryRepository(mock_session)


class TestCreate:
    async def test_creates_user_scoped_memory(
        self, repo: MemoryRepository, mock_session: AsyncMock
    ) -> None:
        user_id = uuid.uuid4()

        await repo.create(user_id, MemoryScope.user, "Remember this fact")

        mock_session.add.assert_called_once()
        mem = mock_session.add.call_args[0][0]
        assert isinstance(mem, Memory)
        assert mem.user_id == user_id
        assert mem.scope == MemoryScope.user
        assert mem.content == "Remember this fact"
        assert mem.workspace_id is None
        assert mem.tags == []

    async def test_creates_workspace_scoped_memory_with_tags(
        self, repo: MemoryRepository, mock_session: AsyncMock
    ) -> None:
        user_id = uuid.uuid4()
        workspace_id = uuid.uuid4()

        await repo.create(
            user_id,
            MemoryScope.workspace,
            "Project context",
            workspace_id=workspace_id,
            tags=["project", "context"],
        )

        mem = mock_session.add.call_args[0][0]
        assert mem.workspace_id == workspace_id
        assert mem.tags == ["project", "context"]


class TestGetByUser:
    async def test_returns_list(self, repo: MemoryRepository, mock_session: AsyncMock) -> None:
        memories = [MagicMock(spec=Memory), MagicMock(spec=Memory)]
        execute_result = MagicMock()
        execute_result.scalars.return_value.all.return_value = memories
        mock_session.execute.return_value = execute_result

        result = await repo.get_by_user(uuid.uuid4())

        assert result == memories

    async def test_returns_empty_list(
        self, repo: MemoryRepository, mock_session: AsyncMock
    ) -> None:
        execute_result = MagicMock()
        execute_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = execute_result

        result = await repo.get_by_user(uuid.uuid4())

        assert result == []


class TestMemoryScopeValues:
    def test_global_scope_has_correct_value(self) -> None:
        assert MemoryScope.global_.value == "global"

    def test_user_scope_has_correct_value(self) -> None:
        assert MemoryScope.user.value == "user"
