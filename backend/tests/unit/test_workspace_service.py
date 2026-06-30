import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.models.workspace import Workspace, WorkspaceMember, WorkspaceMemberRole
from app.services.workspace_service import WorkspaceService


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def service(mock_session: AsyncMock) -> WorkspaceService:
    return WorkspaceService(mock_session)


def _mock_workspace(owner_id: uuid.UUID | None = None) -> MagicMock:
    ws = MagicMock(spec=Workspace)
    ws.id = uuid.uuid4()
    ws.owner_id = owner_id or uuid.uuid4()
    return ws


def _mock_member(role: WorkspaceMemberRole = WorkspaceMemberRole.viewer) -> MagicMock:
    m = MagicMock(spec=WorkspaceMember)
    m.id = uuid.uuid4()
    m.role = role
    m.workspace_id = uuid.uuid4()
    m.user_id = uuid.uuid4()
    return m


class TestCreate:
    async def test_creates_workspace_and_adds_owner_member(
        self, service: WorkspaceService, mock_session: AsyncMock
    ) -> None:
        user_id = uuid.uuid4()
        workspace = _mock_workspace(owner_id=user_id)
        # First execute: get_by_id inside add_member (via get)
        # Simulate create → flush creates workspace, then add_member calls flush again
        mock_session.add = MagicMock()

        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = workspace
        mock_session.execute.return_value = execute_result

        # Patch the repo methods directly on the service's _repo
        service._repo.create = AsyncMock(return_value=workspace)  # type: ignore[method-assign]
        service._repo.add_member = AsyncMock(return_value=_mock_member(WorkspaceMemberRole.owner))  # type: ignore[method-assign]

        result = await service.create(user_id, "My Workspace")

        service._repo.create.assert_awaited_once_with(name="My Workspace", owner_id=user_id)
        service._repo.add_member.assert_awaited_once_with(
            workspace.id, user_id, WorkspaceMemberRole.owner
        )
        assert result is workspace


class TestGet:
    async def test_raises_not_found_when_workspace_missing(self, service: WorkspaceService) -> None:
        service._repo.get_by_id = AsyncMock(return_value=None)  # type: ignore[method-assign]

        with pytest.raises(NotFoundError):
            await service.get(uuid.uuid4(), uuid.uuid4())

    async def test_raises_forbidden_when_not_member(self, service: WorkspaceService) -> None:
        service._repo.get_by_id = AsyncMock(return_value=_mock_workspace())  # type: ignore[method-assign]
        service._repo.get_member = AsyncMock(return_value=None)  # type: ignore[method-assign]

        with pytest.raises(ForbiddenError):
            await service.get(uuid.uuid4(), uuid.uuid4())

    async def test_returns_workspace_and_member(self, service: WorkspaceService) -> None:
        workspace = _mock_workspace()
        member = _mock_member(WorkspaceMemberRole.editor)
        service._repo.get_by_id = AsyncMock(return_value=workspace)  # type: ignore[method-assign]
        service._repo.get_member = AsyncMock(return_value=member)  # type: ignore[method-assign]

        result_ws, result_member = await service.get(uuid.uuid4(), uuid.uuid4())

        assert result_ws is workspace
        assert result_member is member


class TestAddMember:
    async def test_raises_forbidden_when_requester_is_not_owner_or_editor(
        self, service: WorkspaceService
    ) -> None:
        workspace = _mock_workspace()
        viewer_member = _mock_member(WorkspaceMemberRole.viewer)
        service._repo.get_by_id = AsyncMock(return_value=workspace)  # type: ignore[method-assign]
        service._repo.get_member = AsyncMock(return_value=viewer_member)  # type: ignore[method-assign]

        with pytest.raises(ForbiddenError):
            await service.add_member(
                uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), WorkspaceMemberRole.viewer
            )

    async def test_raises_forbidden_when_user_already_member(
        self, service: WorkspaceService
    ) -> None:
        workspace = _mock_workspace()
        owner_member = _mock_member(WorkspaceMemberRole.owner)
        existing_member = _mock_member(WorkspaceMemberRole.viewer)

        call_count = 0

        async def get_member_side_effect(
            workspace_id: uuid.UUID, user_id: uuid.UUID
        ) -> WorkspaceMember | None:
            nonlocal call_count
            call_count += 1
            return owner_member if call_count == 1 else existing_member

        service._repo.get_by_id = AsyncMock(return_value=workspace)  # type: ignore[method-assign]
        service._repo.get_member = AsyncMock(side_effect=get_member_side_effect)  # type: ignore[method-assign]

        with pytest.raises(ForbiddenError):
            await service.add_member(
                uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), WorkspaceMemberRole.viewer
            )
