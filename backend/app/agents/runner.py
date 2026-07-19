"""AgentRunner — orchestrates a full agent run across DB, Redis, and LangGraph."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import redis.asyncio as aioredis
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from app.agents.events import EventPublisher
from app.agents.orchestrator import build_graph
from app.agents.state import AgentState
from app.core.config import settings
from app.core.metrics import agent_runs_total
from app.db.models.agent import AgentRunStatus
from app.db.models.conversation import MessageRole
from app.db.repositories.agent_repository import AgentRepository
from app.db.repositories.message_repository import MessageRepository
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def run_agent(
    *,
    conversation_id: uuid.UUID,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    run_id: uuid.UUID,
) -> None:
    """Execute a full agent run with its own DB session and Redis connection.

    Designed to be called from asyncio.create_task() or an ARQ worker.
    Streams events to Redis; the SSE endpoint forwards them to the client.
    """
    redis_client: Any = aioredis.from_url(  # type: ignore[no-untyped-call]
        settings.REDIS_URL, decode_responses=True
    )
    agent_runs_total.labels(status="started").inc()
    try:
        publisher = EventPublisher(redis_client, str(run_id))
        async with AsyncSessionLocal() as session:
            message_repo = MessageRepository(session)
            agent_repo = AgentRepository(session)

            db_messages = await message_repo.get_recent(conversation_id, limit=40)
            lc_messages: list[Any] = []
            for m in db_messages:
                if m.role == MessageRole.user:
                    lc_messages.append(HumanMessage(content=m.content))
                elif m.role == MessageRole.assistant:
                    lc_messages.append(AIMessage(content=m.content))

            initial_state: AgentState = {
                "messages": lc_messages,
                "conversation_id": str(conversation_id),
                "workspace_id": str(workspace_id),
                "user_id": str(user_id),
                "run_id": str(run_id),
                "stream_key": f"sse:run:{run_id}",
                "token_budget": settings.AGENT_TOKEN_BUDGET,
                "tokens_used": 0,
                "retrieved_chunks": [],
                "web_results": [],
                "memories": [],
                "error": None,
            }

            config = RunnableConfig(
                configurable={
                    "publisher": publisher,
                    "session": session,
                }
            )

            try:
                graph = build_graph()
                final_state: AgentState = await graph.ainvoke(initial_state, config=config)

                last_ai = next(
                    (m for m in reversed(final_state["messages"]) if isinstance(m, AIMessage)),
                    None,
                )
                if last_ai:
                    saved_msg = await message_repo.create(
                        conversation_id=conversation_id,
                        role=MessageRole.assistant,
                        content=str(last_ai.content),
                    )
                    await agent_repo.update_run(
                        run_id,
                        AgentRunStatus.completed,
                        graph_state={"tokens_used": final_state["tokens_used"]},
                    )
                    await session.commit()
                    agent_runs_total.labels(status="completed").inc()
                    await publisher.done(
                        message_id=str(saved_msg.id),
                        input_tokens=final_state["tokens_used"],
                        output_tokens=0,
                    )
                else:
                    await agent_repo.update_run(run_id, AgentRunStatus.completed)
                    await session.commit()
                    agent_runs_total.labels(status="completed").inc()
                    await publisher.done(message_id="", input_tokens=0, output_tokens=0)

            except Exception:
                logger.exception("Agent run failed", extra={"run_id": str(run_id)})
                agent_runs_total.labels(status="failed").inc()
                try:
                    await publisher.error("agent_error", "An error occurred during processing")
                    await agent_repo.update_run(run_id, AgentRunStatus.failed)
                    await session.commit()
                except Exception:
                    logger.exception("Failed to finalise failed run")
                raise
    finally:
        await redis_client.aclose()
