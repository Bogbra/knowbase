"""Semantic similarity search over workspace document chunks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.repositories.document_repository import DocumentRepository


@dataclass
class ChunkResult:
    chunk_id: str
    document_id: str
    content: str
    chunk_index: int
    score: float  # cosine distance (0 = identical, 2 = opposite); lower is better
    metadata: dict[str, Any]


async def vector_search(
    query_embedding: list[float],
    workspace_id: str,
    session: AsyncSession,
    k: int = 8,
    distance_threshold: float | None = None,
) -> list[ChunkResult]:
    """Return the top-k document chunks most similar to query_embedding.

    Chunks whose cosine distance exceeds distance_threshold are dropped.
    Defaults to settings.AGENT_RETRIEVAL_DISTANCE_THRESHOLD.
    """
    import uuid

    threshold = (
        distance_threshold
        if distance_threshold is not None
        else settings.AGENT_RETRIEVAL_DISTANCE_THRESHOLD
    )

    ws_uuid = uuid.UUID(workspace_id)
    repo = DocumentRepository(session)
    rows = await repo.search_similar_chunks(ws_uuid, query_embedding, limit=k)

    return [
        ChunkResult(
            chunk_id=str(chunk.id),
            document_id=str(chunk.document_id),
            content=chunk.content,
            chunk_index=chunk.chunk_index,
            score=distance,
            metadata=chunk.metadata_,
        )
        for chunk, distance in rows
        if distance <= threshold
    ]
