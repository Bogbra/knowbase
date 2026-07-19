"""Web search node — runs Tavily search in parallel with document retrieval."""

from __future__ import annotations

import time
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.events import EventPublisher
from app.agents.state import AgentState
from app.agents.tools.web_search import web_search


async def web_search_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    configurable = config.get("configurable", {})
    publisher: EventPublisher = configurable["publisher"]

    last_human = next(
        (m for m in reversed(state["messages"]) if m.type == "human"),
        None,
    )
    query = str(last_human.content) if last_human else ""

    await publisher.thinking(step="Searching the web", agent="web_search")
    await publisher.tool_call(
        name="web_search",
        input_data={"query": query[:200]},
        agent="web_search",
    )

    t0 = time.monotonic()
    results = await web_search(query, k=5)
    duration_ms = int((time.monotonic() - t0) * 1000)

    await publisher.tool_result(
        name="web_search",
        output={"count": len(results)},
        status="ok",
        duration_ms=duration_ms,
    )

    return {"web_results": results}
