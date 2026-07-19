import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.memory import Memory, MemoryScope


class MemoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, memory_id: uuid.UUID) -> Memory | None:
        result = await self._session.execute(select(Memory).where(Memory.id == memory_id))
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: uuid.UUID) -> list[Memory]:
        result = await self._session.execute(
            select(Memory).where(Memory.user_id == user_id).order_by(Memory.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_workspace(self, workspace_id: uuid.UUID) -> list[Memory]:
        result = await self._session.execute(
            select(Memory)
            .where(Memory.workspace_id == workspace_id)
            .order_by(Memory.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(
        self,
        user_id: uuid.UUID,
        scope: MemoryScope,
        content: str,
        workspace_id: uuid.UUID | None = None,
        tags: list[str] | None = None,
        embedding: list[float] | None = None,
    ) -> Memory:
        memory = Memory(
            user_id=user_id,
            workspace_id=workspace_id,
            scope=scope,
            content=content,
            tags=tags or [],
            embedding=embedding,
            metadata_={},
        )
        self._session.add(memory)
        await self._session.flush()
        await self._session.refresh(memory)
        return memory

    async def search_similar(
        self,
        user_id: uuid.UUID,
        embedding: list[float],
        limit: int = 10,
        workspace_id: uuid.UUID | None = None,
    ) -> list[Memory]:
        stmt = (
            select(Memory)
            .where(
                Memory.user_id == user_id,
                Memory.embedding.isnot(None),
            )
            .order_by(Memory.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        if workspace_id is not None:
            stmt = stmt.where(Memory.workspace_id == workspace_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
