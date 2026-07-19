"""Memory-write node — extracts key facts from the exchange and persists them."""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.events import EventPublisher
from app.agents.state import AgentState
from app.agents.tools.memory_tools import write_memory
from app.core.config import settings
from app.db.models.memory import MemoryScope

logger = logging.getLogger(__name__)

_EXTRACT_PROMPT = """\
Extract up to 3 short, standalone facts worth remembering from this exchange.
Return ONLY a JSON array of strings. Each fact: ≤120 characters, third-person, factual.
If nothing is worth keeping, return [].

Exchange:
{exchange}
"""


async def memory_write_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    configurable = config.get("configurable", {})
    publisher: EventPublisher = configurable["publisher"]
    session: AsyncSession = configurable["session"]

    last_human = next(
        (m for m in reversed(state["messages"]) if m.type == "human"),
        None,
    )
    last_ai = next(
        (m for m in reversed(state["messages"]) if isinstance(m, AIMessage)),
        None,
    )

    has_ai_key = bool(settings.ANTHROPIC_API_KEY or settings.OPENAI_API_KEY)
    if not last_human or not last_ai or not has_ai_key:
        return {}

    await publisher.thinking(step="Consolidating memories", agent="memory")

    exchange = f"User: {str(last_human.content)[:500]}\nAssistant: {str(last_ai.content)[:500]}"
    prompt = _EXTRACT_PROMPT.format(exchange=exchange)

    try:
        if settings.ANTHROPIC_API_KEY:
            import anthropic

            aclient = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            resp = await aclient.messages.create(
                model=settings.AGENT_FALLBACK_MODEL,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text.strip()  # type: ignore[union-attr]
        else:
            import openai

            oclient = openai.AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_API_BASE or None,
            )
            oai_resp = await oclient.chat.completions.create(
                model=settings.OPENAI_AGENT_FALLBACK_MODEL,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = (oai_resp.choices[0].message.content or "[]").strip()

        facts: list[Any] = json.loads(raw)
        if not isinstance(facts, list):
            return {}
    except Exception:
        logger.exception("memory_write extraction failed")
        return {}

    for fact in facts[:3]:
        if not isinstance(fact, str) or not fact.strip():
            continue
        try:
            await write_memory(
                user_id=state["user_id"],
                content=fact.strip(),
                scope=MemoryScope.workspace,
                session=session,
                workspace_id=state["workspace_id"],
            )
        except Exception:
            logger.exception("Failed to persist memory fact")

    return {}
