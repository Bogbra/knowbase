"""SSE streaming endpoint — reads agent-run events from Redis Streams."""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user, get_db_dep
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.models.user import User
from app.db.repositories.agent_repository import AgentRepository
from app.db.repositories.conversation_repository import ConversationRepository
from app.db.repositories.workspace_repository import WorkspaceRepository

router = APIRouter(tags=["stream"])
logger = logging.getLogger(__name__)

_SSE_TIMEOUT_S = 120
_BLOCK_MS = 3000
_HEARTBEAT_INTERVAL_S = 15


async def _read_stream(
    redis_client: Any,
    stream_key: str,
) -> AsyncGenerator[str, None]:
    last_id = "0"
    deadline = time.monotonic() + _SSE_TIMEOUT_S
    last_heartbeat = time.monotonic()

    while time.monotonic() < deadline:
        remaining_ms = max(1, int((deadline - time.monotonic()) * 1000))
        block_ms = min(_BLOCK_MS, remaining_ms)

        try:
            entries = await redis_client.xread({stream_key: last_id}, block=block_ms, count=50)
        except Exception:
            logger.exception("SSE stream read error", extra={"key": stream_key})
            break

        if entries:
            for _, messages in entries:
                for entry_id, data in messages:
                    payload_str: str = data.get("payload", "{}")
                    try:
                        payload: dict[str, object] = json.loads(payload_str)
                    except json.JSONDecodeError:
                        continue
                    yield f"data: {json.dumps(payload)}\n\n"
                    last_id = entry_id
                    if payload.get("type") in ("done", "error"):
                        return
        else:
            now = time.monotonic()
            if now - last_heartbeat >= _HEARTBEAT_INTERVAL_S:
                yield ": heartbeat\n\n"
                last_heartbeat = now


@router.get("/conversations/{conversation_id}/stream")
async def stream_agent_run(
    conversation_id: uuid.UUID,
    run_id: uuid.UUID = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_dep),
) -> StreamingResponse:
    conv_repo = ConversationRepository(db)
    conversation = await conv_repo.get_by_id(conversation_id)
    if conversation is None:
        raise NotFoundError("Conversation", str(conversation_id))

    ws_repo = WorkspaceRepository(db)
    member = await ws_repo.get_member(conversation.workspace_id, current_user.id)
    if member is None:
        raise ForbiddenError("Not a member of this workspace")

    agent_repo = AgentRepository(db)
    run = await agent_repo.get_run_by_id(run_id)
    if run is None or run.conversation_id != conversation_id:
        raise NotFoundError("AgentRun", str(run_id))

    stream_key = f"sse:run:{run_id}"
    redis_client: Any = aioredis.from_url(  # type: ignore[no-untyped-call]
        settings.REDIS_URL, decode_responses=True
    )

    async def generate() -> AsyncGenerator[str, None]:
        try:
            async for event in _read_stream(redis_client, stream_key):
                yield event
        finally:
            await redis_client.aclose()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
