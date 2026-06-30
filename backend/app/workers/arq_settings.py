"""ARQ WorkerSettings — run with: uv run arq app.workers.arq_settings.WorkerSettings"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from arq.connections import RedisSettings

from app.core.config import settings
from app.workers.ingest import ingest_document_task

logger = logging.getLogger(__name__)


async def run_agent_task(
    ctx: dict[str, Any],
    conversation_id: str,
    workspace_id: str,
    user_id: str,
    run_id: str,
) -> None:
    from app.agents.runner import run_agent

    await run_agent(
        conversation_id=uuid.UUID(conversation_id),
        workspace_id=uuid.UUID(workspace_id),
        user_id=uuid.UUID(user_id),
        run_id=uuid.UUID(run_id),
    )


async def startup(ctx: dict[str, Any]) -> None:
    logger.info("worker_started")


async def shutdown(ctx: dict[str, Any]) -> None:
    logger.info("worker_stopped")


class WorkerSettings:
    functions = [run_agent_task, ingest_document_task]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 900
