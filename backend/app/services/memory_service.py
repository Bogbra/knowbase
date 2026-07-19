import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.embed import embed_text
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.models.memory import Memory, MemoryScope
from app.db.repositories.memory_repository import MemoryRepository


class MemoryService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = MemoryRepository(session)

    async def create(
        self,
        user_id: uuid.UUID,
        scope: MemoryScope,
        content: str,
        workspace_id: uuid.UUID | None = None,
        tags: list[str] | None = None,
    ) -> Memory:
        embedding = await embed_text(content)
        return await self._repo.create(
            user_id=user_id,
            scope=scope,
            content=content,
            workspace_id=workspace_id,
            tags=tags,
            embedding=embedding,
        )

    async def list_for_user(self, user_id: uuid.UUID) -> list[Memory]:
        return await self._repo.get_by_user(user_id)

    async def get(self, memory_id: uuid.UUID, user_id: uuid.UUID) -> Memory:
        memory = await self._repo.get_by_id(memory_id)
        if memory is None:
            raise NotFoundError("Memory", str(memory_id))
        if memory.user_id != user_id:
            raise ForbiddenError("Not your memory")
        return memory

    async def delete(self, memory_id: uuid.UUID, user_id: uuid.UUID) -> None:
        memory = await self.get(memory_id, user_id)
        await self._repo._session.delete(memory)
