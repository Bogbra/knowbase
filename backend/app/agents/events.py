"""SSE event publisher — writes to Redis Stream, consumed by the SSE endpoint."""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


class EventPublisher:
    def __init__(self, redis: aioredis.Redis, run_id: str) -> None:
        self._redis = redis
        self._run_id = run_id
        self._key = f"sse:run:{run_id}"

    async def _push(self, event_type: str, data: dict[str, Any]) -> None:
        payload = json.dumps({"type": event_type, "data": data})
        try:
            await self._redis.xadd(
                self._key,
                {"payload": payload},
                maxlen=500,
                approximate=True,
            )
            await self._redis.expire(self._key, settings.SSE_STREAM_TTL_S)
        except Exception:
            logger.exception("Failed to publish SSE event", extra={"run_id": self._run_id})

    async def thinking(self, step: str, agent: str) -> None:
        await self._push("thinking", {"step": step, "agent": agent})

    async def tool_call(self, name: str, input_data: dict[str, Any], agent: str) -> None:
        await self._push("tool_call", {"name": name, "input": input_data, "agent": agent})

    async def tool_result(
        self,
        name: str,
        output: dict[str, Any],
        status: str,
        duration_ms: int,
    ) -> None:
        await self._push(
            "tool_result",
            {"name": name, "output": output, "status": status, "duration_ms": duration_ms},
        )

    async def token(self, text: str) -> None:
        await self._push("token", {"text": text})

    async def done(self, message_id: str, input_tokens: int, output_tokens: int) -> None:
        await self._push(
            "done",
            {
                "message_id": message_id,
                "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
            },
        )

    async def sources(self, documents: list[dict[str, str]]) -> None:
        await self._push("sources", {"documents": documents})

    async def error(self, code: str, message: str) -> None:
        await self._push("error", {"code": code, "message": message})
