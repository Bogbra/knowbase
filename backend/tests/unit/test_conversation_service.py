import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.models.conversation import Conversation, Message, MessageRole
from app.db.models.workspace import Workspace, WorkspaceMember, WorkspaceMemberRole
from app.services.conversation_service import ConversationService


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(mock_session: AsyncMock) -> ConversationService:
    return ConversationService(mock_session)


def _mock_workspace() -> MagicMock:
    ws = MagicMock(spec=Workspace)
    ws.id = uuid.uuid4()
    return ws


def _mock_member() -> MagicMock:
    m = MagicMock(spec=WorkspaceMember)
    m.role = WorkspaceMemberRole.editor
    return m


def _mock_conversation(workspace_id: uuid.UUID | None = None) -> MagicMock:
    c = MagicMock(spec=Conversation)
    c.id = uuid.uuid4()
    c.workspace_id = workspace_id or uuid.uuid4()
    return c


class TestCreate:
    async def test_raises_not_found_when_workspace_missing(
        self, service: ConversationService
    ) -> None:
        service._ws_repo.get_by_id = AsyncMock(return_value=None)  # type: ignore[method-assign]

        with pytest.raises(NotFoundError):
            await service.create(uuid.uuid4(), uuid.uuid4())

    async def test_raises_forbidden_when_not_member(self, service: ConversationService) -> None:
        service._ws_repo.get_by_id = AsyncMock(return_value=_mock_workspace())  # type: ignore[method-assign]
        service._ws_repo.get_member = AsyncMock(return_value=None)  # type: ignore[method-assign]

        with pytest.raises(ForbiddenError):
            await service.create(uuid.uuid4(), uuid.uuid4())

    async def test_creates_conversation_for_member(self, service: ConversationService) -> None:
        workspace_id = uuid.uuid4()
        user_id = uuid.uuid4()
        conv = _mock_conversation(workspace_id)

        service._ws_repo.get_by_id = AsyncMock(return_value=_mock_workspace())  # type: ignore[method-assign]
        service._ws_repo.get_member = AsyncMock(return_value=_mock_member())  # type: ignore[method-assign]
        service._conv_repo.create = AsyncMock(return_value=conv)  # type: ignore[method-assign]

        result = await service.create(workspace_id, user_id, "My Chat")

        service._conv_repo.create.assert_awaited_once_with(workspace_id, user_id, "My Chat")
        assert result is conv


class TestGet:
    async def test_raises_not_found_when_conversation_missing(
        self, service: ConversationService
    ) -> None:
        service._conv_repo.get_by_id = AsyncMock(return_value=None)  # type: ignore[method-assign]

        with pytest.raises(NotFoundError):
            await service.get(uuid.uuid4(), uuid.uuid4())

    async def test_returns_conversation_for_workspace_member(
        self, service: ConversationService
    ) -> None:
        conv = _mock_conversation()
        service._conv_repo.get_by_id = AsyncMock(return_value=conv)  # type: ignore[method-assign]
        service._ws_repo.get_by_id = AsyncMock(return_value=_mock_workspace())  # type: ignore[method-assign]
        service._ws_repo.get_member = AsyncMock(return_value=_mock_member())  # type: ignore[method-assign]

        result = await service.get(conv.id, uuid.uuid4())

        assert result is conv


class TestAddMessage:
    async def test_adds_message_to_conversation(self, service: ConversationService) -> None:
        conv = _mock_conversation()
        msg = MagicMock(spec=Message)
        msg.role = MessageRole.user
        msg.content = "Hello"

        service._conv_repo.get_by_id = AsyncMock(return_value=conv)  # type: ignore[method-assign]
        service._ws_repo.get_by_id = AsyncMock(return_value=_mock_workspace())  # type: ignore[method-assign]
        service._ws_repo.get_member = AsyncMock(return_value=_mock_member())  # type: ignore[method-assign]
        service._msg_repo.create = AsyncMock(return_value=msg)  # type: ignore[method-assign]

        result = await service.add_message(conv.id, uuid.uuid4(), MessageRole.user, "Hello")

        service._msg_repo.create.assert_awaited_once_with(conv.id, MessageRole.user, "Hello")
        assert result is msg
