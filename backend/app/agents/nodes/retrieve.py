"""Retrieval node — query decomposition + parallel semantic search over workspace chunks."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from langchain_core.runnables import RunnableConfig
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.embed import embed_text
from app.agents.events import EventPublisher
from app.agents.state import AgentState
from app.agents.tools.vector_search import ChunkResult, vector_search
from app.core.config import settings
from app.db.repositories.document_repository import DocumentRepository

_DECOMPOSE_SYSTEM = (
    "Extract up to 5 focused, self-contained search queries from the user question. "
    "Each query should cover exactly one specific concept or sub-topic. "
    "Reply with a JSON array of strings only — no explanation, no markdown. "
    'Example: ["Pressefreiheit Begriff", "Medienkonvergenz Definition", "Urheberrecht Schranken"]'
)

_MAX_MERGED_CHUNKS = 25
_PER_QUERY_K = 8


async def _decompose_query(query: str) -> list[str]:
    """Split a multi-part question into focused sub-queries via a lightweight LLM call.

    Falls back to the original query as a single-element list on any error.
    """
    raw = ""
    try:
        if settings.ANTHROPIC_API_KEY:
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            msg = await client.messages.create(
                model=settings.AGENT_FALLBACK_MODEL,
                max_tokens=200,
                system=_DECOMPOSE_SYSTEM,
                messages=[{"role": "user", "content": query[:2000]}],
            )
            try:
                raw = str(msg.content[0].text)  # type: ignore[union-attr]
            except (IndexError, AttributeError):
                raw = ""
        elif settings.OPENAI_API_KEY:
            import openai

            oai = openai.AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_API_BASE or None,
            )
            resp = await oai.chat.completions.create(
                model=settings.OPENAI_AGENT_FALLBACK_MODEL,
                max_tokens=200,
                messages=[
                    {"role": "system", "content": _DECOMPOSE_SYSTEM},
                    {"role": "user", "content": query[:2000]},
                ],
            )
            choice = resp.choices[0] if resp.choices else None
            raw = choice.message.content or "" if choice is not None else ""

        if raw:
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if 0 <= start < end:
                parsed: Any = json.loads(raw[start:end])
                if isinstance(parsed, list):
                    seen: set[str] = set()
                    result: list[str] = []
                    for item in parsed:
                        q = str(item).strip()
                        if q and q not in seen:
                            seen.add(q)
                            result.append(q)
                    if result:
                        return result[:5]
    except Exception:  # noqa: S110 — best-effort decomposition; original query used as fallback
        pass

    return [query]


async def retrieval_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    configurable = config.get("configurable", {})
    publisher: EventPublisher = configurable["publisher"]
    session: AsyncSession = configurable["session"]

    last_human = next(
        (m for m in reversed(state["messages"]) if m.type == "human"),
        None,
    )
    query = str(last_human.content) if last_human else ""

    await publisher.thinking(step="Searching workspace documents", agent="retrieval")

    # Decompose multi-part question so each sub-topic gets its own retrieval pass
    sub_queries = await _decompose_query(query)

    await publisher.tool_call(
        name="vector_search",
        input_data={
            "sub_queries": [q[:200] for q in sub_queries],
            "k_per_query": _PER_QUERY_K,
        },
        agent="retrieval",
    )

    t0 = time.monotonic()

    seen_ids: set[str] = set()
    merged: list[ChunkResult] = []
    for sub_q in sub_queries:
        embedding = await embed_text(sub_q)
        results = await vector_search(
            query_embedding=embedding,
            workspace_id=state["workspace_id"],
            session=session,
            k=_PER_QUERY_K,
        )
        for chunk in results:
            if chunk.chunk_id not in seen_ids:
                seen_ids.add(chunk.chunk_id)
                merged.append(chunk)

    # Sort by relevance score (lower cosine distance = more relevant), cap total
    merged.sort(key=lambda c: c.score)
    merged = merged[:_MAX_MERGED_CHUNKS]

    duration_ms = int((time.monotonic() - t0) * 1000)

    doc_repo = DocumentRepository(session)
    docs = await doc_repo.get_by_workspace(uuid.UUID(state["workspace_id"]))
    doc_name_map = {str(d.id): d.name for d in docs}

    chunk_dicts = [
        {
            "chunk_id": c.chunk_id,
            "document_id": c.document_id,
            "document_name": doc_name_map.get(c.document_id, "Unknown"),
            "content": c.content,
            "chunk_index": c.chunk_index,
            "chapter": str(c.metadata.get("chapter", "")) if c.metadata else "",
            "distance": round(c.score, 4),
        }
        for c in merged
    ]

    await publisher.tool_result(
        name="vector_search",
        output={"chunks": len(merged), "sub_queries": len(sub_queries)},
        status="ok",
        duration_ms=duration_ms,
    )

    return {"retrieved_chunks": chunk_dicts}
