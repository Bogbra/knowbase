"""Tests for EventPublisher."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.events import EventPublisher


def _make_publisher() -> tuple[EventPublisher, AsyncMock]:
    redis_mock = MagicMock()
    redis_mock.xadd = AsyncMock()
    redis_mock.expire = AsyncMock()
    publisher = EventPublisher(redis_mock, "test-run-id")
    return publisher, redis_mock


@pytest.mark.asyncio
async def test_thinking_event() -> None:
    publisher, redis_mock = _make_publisher()
    await publisher.thinking(step="doing work", agent="orchestrator")

    redis_mock.xadd.assert_awaited_once()
    args = redis_mock.xadd.call_args
    payload = json.loads(args[0][1]["payload"])
    assert payload["type"] == "thinking"
    assert payload["data"]["step"] == "doing work"
    assert payload["data"]["agent"] == "orchestrator"


@pytest.mark.asyncio
async def test_tool_call_event() -> None:
    publisher, redis_mock = _make_publisher()
    await publisher.tool_call(name="vector_search", input_data={"k": 5}, agent="retrieval")

    payload = json.loads(redis_mock.xadd.call_args[0][1]["payload"])
    assert payload["type"] == "tool_call"
    assert payload["data"]["name"] == "vector_search"
    assert payload["data"]["input"] == {"k": 5}


@pytest.mark.asyncio
async def test_tool_result_event() -> None:
    publisher, redis_mock = _make_publisher()
    await publisher.tool_result(
        name="vector_search", output={"count": 3}, status="ok", duration_ms=42
    )

    payload = json.loads(redis_mock.xadd.call_args[0][1]["payload"])
    assert payload["type"] == "tool_result"
    assert payload["data"]["status"] == "ok"
    assert payload["data"]["duration_ms"] == 42


@pytest.mark.asyncio
async def test_token_event() -> None:
    publisher, redis_mock = _make_publisher()
    await publisher.token("Hello")

    payload = json.loads(redis_mock.xadd.call_args[0][1]["payload"])
    assert payload["type"] == "token"
    assert payload["data"]["text"] == "Hello"


@pytest.mark.asyncio
async def test_done_event() -> None:
    publisher, redis_mock = _make_publisher()
    await publisher.done(message_id="msg-123", input_tokens=100, output_tokens=200)

    payload = json.loads(redis_mock.xadd.call_args[0][1]["payload"])
    assert payload["type"] == "done"
    assert payload["data"]["message_id"] == "msg-123"
    assert payload["data"]["usage"]["input_tokens"] == 100
    assert payload["data"]["usage"]["output_tokens"] == 200


@pytest.mark.asyncio
async def test_error_event() -> None:
    publisher, redis_mock = _make_publisher()
    await publisher.error(code="agent_error", message="something went wrong")

    payload = json.loads(redis_mock.xadd.call_args[0][1]["payload"])
    assert payload["type"] == "error"
    assert payload["data"]["code"] == "agent_error"


@pytest.mark.asyncio
async def test_stream_key_format() -> None:
    publisher, redis_mock = _make_publisher()
    await publisher.token("x")
    stream_key = redis_mock.xadd.call_args[0][0]
    assert stream_key == "sse:run:test-run-id"


@pytest.mark.asyncio
async def test_redis_failure_does_not_raise() -> None:
    redis_mock = MagicMock()
    redis_mock.xadd = AsyncMock(side_effect=ConnectionError("Redis down"))
    redis_mock.expire = AsyncMock()
    publisher = EventPublisher(redis_mock, "run-x")
    # Should not raise even when Redis is unavailable
    await publisher.token("silent failure")
