import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models.conversation import Conversation, Message, MessageRole
from app.db.repositories.conversation_repository import ConversationRepository
from app.db.repositories.message_repository import MessageRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    return session


class TestConversationRepository:
    @pytest.fixture
    def repo(self, mock_session: AsyncMock) -> ConversationRepository:
        return ConversationRepository(mock_session)

    async def test_get_by_id_found(
        self, repo: ConversationRepository, mock_session: AsyncMock
    ) -> None:
        expected = MagicMock(spec=Conversation)
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = expected
        mock_session.execute.return_value = execute_result

        result = await repo.get_by_id(uuid.uuid4())

        assert result is expected

    async def test_get_by_id_not_found(
        self, repo: ConversationRepository, mock_session: AsyncMock
    ) -> None:
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = execute_result

        result = await repo.get_by_id(uuid.uuid4())

        assert result is None

    async def test_create_uses_provided_title(
        self, repo: ConversationRepository, mock_session: AsyncMock
    ) -> None:
        workspace_id = uuid.uuid4()
        user_id = uuid.uuid4()

        await repo.create(workspace_id, user_id, "My Chat")

        mock_session.add.assert_called_once()
        conv = mock_session.add.call_args[0][0]
        assert isinstance(conv, Conversation)
        assert conv.title == "My Chat"
        assert conv.workspace_id == workspace_id
        assert conv.user_id == user_id

    async def test_create_default_title(
        self, repo: ConversationRepository, mock_session: AsyncMock
    ) -> None:
        await repo.create(uuid.uuid4(), uuid.uuid4())

        conv = mock_session.add.call_args[0][0]
        assert conv.title == "New conversation"


class TestMessageRepository:
    @pytest.fixture
    def repo(self, mock_session: AsyncMock) -> MessageRepository:
        return MessageRepository(mock_session)

    async def test_create_message(self, repo: MessageRepository, mock_session: AsyncMock) -> None:
        conversation_id = uuid.uuid4()

        await repo.create(conversation_id, MessageRole.user, "Hello!")

        mock_session.add.assert_called_once()
        msg = mock_session.add.call_args[0][0]
        assert isinstance(msg, Message)
        assert msg.role == MessageRole.user
        assert msg.content == "Hello!"
        assert msg.conversation_id == conversation_id

    async def test_get_by_conversation_returns_list(
        self, repo: MessageRepository, mock_session: AsyncMock
    ) -> None:
        messages = [MagicMock(spec=Message), MagicMock(spec=Message)]
        execute_result = MagicMock()
        execute_result.scalars.return_value.all.return_value = messages
        mock_session.execute.return_value = execute_result

        result = await repo.get_by_conversation(uuid.uuid4())

        assert result == messages
