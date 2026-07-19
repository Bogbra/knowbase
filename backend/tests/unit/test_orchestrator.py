"""Unit tests for the orchestrator routing function."""

from unittest.mock import patch

from app.agents.orchestrator import _RETRIEVAL_SUFFICIENT_COUNT, _route_after_retrieval
from app.agents.state import AgentState


def _make_state(chunks: list[dict]) -> AgentState:  # type: ignore[type-arg]
    return AgentState(
        messages=[],
        conversation_id="conv-1",
        workspace_id="ws-1",
        user_id="user-1",
        run_id="run-1",
        stream_key="stream-1",
        token_budget=10_000,
        tokens_used=0,
        retrieved_chunks=chunks,
        web_results=[],
        memories=[],
        error=None,
    )


def _chunk(distance: float = 0.1) -> dict:  # type: ignore[type-arg]
    return {"chunk_id": "c1", "content": "text", "distance": distance}


class TestRouteAfterRetrieval:
    def test_no_tavily_key_always_skips_web_search(self) -> None:
        state = _make_state([])  # zero chunks — would normally trigger web search
        with patch("app.agents.orchestrator.settings") as mock_settings:
            mock_settings.TAVILY_API_KEY = ""
            result = _route_after_retrieval(state)
        assert result == "synthesize"

    def test_enough_chunks_skips_web_search(self) -> None:
        chunks = [_chunk() for _ in range(_RETRIEVAL_SUFFICIENT_COUNT)]
        state = _make_state(chunks)
        with patch("app.agents.orchestrator.settings") as mock_settings:
            mock_settings.TAVILY_API_KEY = "tvly-test-key"
            result = _route_after_retrieval(state)
        assert result == "synthesize"

    def test_too_few_chunks_triggers_web_search(self) -> None:
        chunks = [_chunk() for _ in range(_RETRIEVAL_SUFFICIENT_COUNT - 1)]
        state = _make_state(chunks)
        with patch("app.agents.orchestrator.settings") as mock_settings:
            mock_settings.TAVILY_API_KEY = "tvly-test-key"
            result = _route_after_retrieval(state)
        assert result == "web_search"
