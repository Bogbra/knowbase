import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.models.conversation import Conversation, Message, MessageRole
from app.db.repositories.conversation_repository import ConversationRepository
from app.db.repositories.message_repository import MessageRepository
from app.db.repositories.workspace_repository import WorkspaceRepository


class ConversationService:
    def __init__(self, session: AsyncSession) -> None:
        self._conv_repo = ConversationRepository(session)
        self._msg_repo = MessageRepository(session)
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
        title: str = "New conversation",
    ) -> Conversation:
        await self._check_workspace_access(workspace_id, user_id)
        return await self._conv_repo.create(workspace_id, user_id, title)

    async def list_by_workspace(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[Conversation]:
        await self._check_workspace_access(workspace_id, user_id)
        return await self._conv_repo.get_by_workspace(workspace_id)

    async def get(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> Conversation:
        conv = await self._conv_repo.get_by_id(conversation_id)
        if conv is None:
            raise NotFoundError("Conversation", str(conversation_id))
        await self._check_workspace_access(conv.workspace_id, user_id)
        return conv

    async def delete(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> None:
        conv = await self.get(conversation_id, user_id)
        await self._conv_repo._session.delete(conv)

    async def list_messages(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> list[Message]:
        await self.get(conversation_id, user_id)
        return await self._msg_repo.get_by_conversation(conversation_id)

    async def add_message(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        role: MessageRole,
        content: str,
    ) -> Message:
        await self.get(conversation_id, user_id)
        return await self._msg_repo.create(conversation_id, role, content)
