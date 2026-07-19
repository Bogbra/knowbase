import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models.workspace import Workspace, WorkspaceMember, WorkspaceMemberRole
from app.db.repositories.workspace_repository import WorkspaceRepository


def _execute_returning(value: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    mock = AsyncMock()
    mock.return_value = result
    return mock


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def repo(mock_session: AsyncMock) -> WorkspaceRepository:
    return WorkspaceRepository(mock_session)


class TestGetById:
    async def test_returns_workspace_when_found(
        self, repo: WorkspaceRepository, mock_session: AsyncMock
    ) -> None:
        expected = MagicMock(spec=Workspace)
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = expected
        mock_session.execute.return_value = execute_result

        result = await repo.get_by_id(uuid.uuid4())

        assert result is expected
        mock_session.execute.assert_awaited_once()

    async def test_returns_none_when_not_found(
        self, repo: WorkspaceRepository, mock_session: AsyncMock
    ) -> None:
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = execute_result

        result = await repo.get_by_id(uuid.uuid4())

        assert result is None


class TestCreate:
    async def test_creates_workspace_and_flushes(
        self, repo: WorkspaceRepository, mock_session: AsyncMock
    ) -> None:
        owner_id = uuid.uuid4()

        await repo.create("My Workspace", owner_id)

        mock_session.add.assert_called_once()
        created = mock_session.add.call_args[0][0]
        assert isinstance(created, Workspace)
        assert created.name == "My Workspace"
        assert created.owner_id == owner_id
        mock_session.flush.assert_awaited_once()


class TestAddMember:
    async def test_adds_member_with_default_viewer_role(
        self, repo: WorkspaceRepository, mock_session: AsyncMock
    ) -> None:
        workspace_id = uuid.uuid4()
        user_id = uuid.uuid4()

        await repo.add_member(workspace_id, user_id)

        mock_session.add.assert_called_once()
        member = mock_session.add.call_args[0][0]
        assert isinstance(member, WorkspaceMember)
        assert member.workspace_id == workspace_id
        assert member.user_id == user_id
        assert member.role == WorkspaceMemberRole.viewer

    async def test_adds_member_with_explicit_role(
        self, repo: WorkspaceRepository, mock_session: AsyncMock
    ) -> None:
        await repo.add_member(uuid.uuid4(), uuid.uuid4(), WorkspaceMemberRole.editor)

        member = mock_session.add.call_args[0][0]
        assert member.role == WorkspaceMemberRole.editor
