"""Memory-read node — fetches relevant long-term memories for the user."""

from __future__ import annotations

import time
from typing import Any

from langchain_core.runnables import RunnableConfig
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.embed import embed_text
from app.agents.events import EventPublisher
from app.agents.state import AgentState
from app.agents.tools.memory_tools import read_memory
from app.core.config import settings


async def memory_read_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    configurable = config.get("configurable", {})
    publisher: EventPublisher = configurable["publisher"]
    session: AsyncSession = configurable["session"]

    last_human = next(
        (m for m in reversed(state["messages"]) if m.type == "human"),
        None,
    )
    query = str(last_human.content) if last_human else ""

    await publisher.thinking(step="Reading relevant memories", agent="memory")
    await publisher.tool_call(
        name="read_memory",
        input_data={"k": settings.AGENT_MEMORY_K},
        agent="memory",
    )

    t0 = time.monotonic()
    embedding = await embed_text(query)
    memories = await read_memory(
        user_id=state["user_id"],
        query_embedding=embedding,
        session=session,
        k=settings.AGENT_MEMORY_K,
    )
    duration_ms = int((time.monotonic() - t0) * 1000)

    memory_dicts = [
        {
            "memory_id": m.memory_id,
            "content": m.content,
            "scope": m.scope,
            "tags": m.tags,
        }
        for m in memories
    ]

    await publisher.tool_result(
        name="read_memory",
        output={"count": len(memories)},
        status="ok",
        duration_ms=duration_ms,
    )

    return {"memories": memory_dicts}
