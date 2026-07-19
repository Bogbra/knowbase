"""Agent tools for reading from and writing to long-term memory."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.embed import embed_text
from app.db.models.memory import MemoryScope
from app.db.repositories.memory_repository import MemoryRepository


@dataclass
class MemoryResult:
    memory_id: str
    content: str
    scope: str
    tags: list[str]
    metadata: dict[str, Any]


async def read_memory(
    user_id: str,
    query_embedding: list[float],
    session: AsyncSession,
    scope: MemoryScope | None = None,
    k: int = 5,
) -> list[MemoryResult]:
    """Return the k most relevant memories for the given user and embedding."""
    import uuid

    repo = MemoryRepository(session)
    memories = await repo.search_similar(uuid.UUID(user_id), query_embedding, limit=k)
    results = []
    for mem in memories:
        if scope is not None and mem.scope != scope:
            continue
        results.append(
            MemoryResult(
                memory_id=str(mem.id),
                content=mem.content,
                scope=str(mem.scope),
                tags=mem.tags,
                metadata=mem.metadata_,
            )
        )
    return results


async def write_memory(
    user_id: str,
    content: str,
    scope: MemoryScope,
    session: AsyncSession,
    tags: list[str] | None = None,
    workspace_id: str | None = None,
) -> MemoryResult:
    """Persist a new memory entry for the given user."""
    import uuid

    embedding = await embed_text(content)
    repo = MemoryRepository(session)
    ws_uuid = uuid.UUID(workspace_id) if workspace_id else None
    mem = await repo.create(
        user_id=uuid.UUID(user_id),
        scope=scope,
        content=content,
        workspace_id=ws_uuid,
        tags=tags,
        embedding=embedding,
    )
    return MemoryResult(
        memory_id=str(mem.id),
        content=mem.content,
        scope=str(mem.scope),
        tags=mem.tags,
        metadata=mem.metadata_,
    )
