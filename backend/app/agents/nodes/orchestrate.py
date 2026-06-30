"""Orchestrator node — decomposes the user request and emits a thinking event."""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig

from app.agents.events import EventPublisher
from app.agents.sanitizer import sanitize_user_content
from app.agents.state import AgentState


async def orchestrator_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    configurable = config.get("configurable", {})
    publisher: EventPublisher = configurable["publisher"]

    # Grab the last human message; sanitize before any LLM context
    last_human = next(
        (m for m in reversed(state["messages"]) if m.type == "human"),
        None,
    )
    raw_content = last_human.content if last_human else ""
    clean_content = sanitize_user_content(
        raw_content if isinstance(raw_content, str) else str(raw_content)
    )

    await publisher.thinking(
        step=f"Analysing: {clean_content[:120]}{'…' if len(clean_content) > 120 else ''}",
        agent="orchestrator",
    )

    return {}
