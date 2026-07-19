"""Retrieval recall — checks whether expected chunks appear in top-k results.

Recall@k: for each question with an expected_doc set, embeds the query,
runs vector_search, and checks whether at least one returned chunk belongs to
the expected document (and optionally the expected chapter).

Requires OPENAI_API_KEY and a live database with the eval corpus ingested.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.embed import embed_text
from app.agents.tools.vector_search import vector_search
from app.db.models.document import Document


async def recall_at_k(
    question: str,
    expected_doc: str,
    workspace_id: str,
    session: AsyncSession,
    expected_chapter: str | None = None,
    k: int = 8,
) -> bool:
    """Return True if the expected document appears in the top-k retrieval results.

    When expected_chapter is given, at least one chunk must also match the chapter.
    Uses distance_threshold=1.0 (broad) so ranking, not absolute score, is tested.
    """
    embedding = await embed_text(question)
    results = await vector_search(
        query_embedding=embedding,
        workspace_id=workspace_id,
        session=session,
        k=k,
        distance_threshold=1.0,
    )

    # Map document names to IDs within this workspace
    rows = await session.execute(
        select(Document.id, Document.name).where(Document.workspace_id == uuid.UUID(workspace_id))
    )
    name_to_id = {row.name: str(row.id) for row in rows.all()}
    expected_id = name_to_id.get(expected_doc)
    if expected_id is None:
        return False

    for chunk in results:
        if chunk.document_id != expected_id:
            continue
        if expected_chapter is None:
            return True
        chunk_chapter = str(chunk.metadata.get("chapter", "")).strip()
        if chunk_chapter == expected_chapter:
            return True
    return False


async def evaluate_recall_dataset(
    questions: list[dict[str, Any]],
    session: AsyncSession,
    workspace_id: str,
    k: int = 8,
) -> dict[str, Any]:
    """Compute Recall@k over golden questions that have expected_doc set.

    OOD questions (expected_no_source=True) are excluded from the metric.

    Returns:
      recall_at_k   float  — fraction of in-scope questions with a hit
      n_evaluated   int    — number of questions evaluated
      n_hits        int    — number of questions with a hit
      missed        list   — question IDs that were not hit
    """
    evaluated = 0
    hits = 0
    missed: list[str] = []

    for q in questions:
        if q.get("expected_no_source"):
            continue
        expected_doc = q.get("expected_doc")
        if not expected_doc:
            continue
        expected_chapter = q.get("expected_chapter") or None

        hit = await recall_at_k(
            question=str(q["question"]),
            expected_doc=str(expected_doc),
            expected_chapter=str(expected_chapter) if expected_chapter else None,
            workspace_id=workspace_id,
            session=session,
            k=k,
        )
        evaluated += 1
        if hit:
            hits += 1
        else:
            missed.append(str(q.get("id", "?")))

    recall = hits / evaluated if evaluated else 1.0
    return {
        "recall_at_k": recall,
        "n_evaluated": evaluated,
        "n_hits": hits,
        "missed": missed,
    }
