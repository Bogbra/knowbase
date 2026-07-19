"""Regression test — synthesize node fires exactly once despite fan-in from two paths.

The production graph has two paths into synthesize:
  direct:     orchestrator → retrieval → synthesize
  web_search: orchestrator → retrieval → web_search → synthesize

In both cases memory_read also feeds synthesize:
  orchestrator → memory_read → synthesize

Without defer=True on the synthesize node, LangGraph fires it once per completed
upstream path — causing a double-call when memory_read finishes while retrieval
is still in flight. This test pins the fix: synthesize must fire exactly once,
regardless of which routing branch is taken.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from app.agents.orchestrator import _RETRIEVAL_SUFFICIENT_COUNT, _route_after_retrieval
from app.agents.state import AgentState

_BASE_STATE: dict[str, Any] = {
    "messages": [],
    "conversation_id": "test-conv",
    "workspace_id": "test-ws",
    "user_id": "test-user",
    "run_id": "test-run",
    "stream_key": "test-stream",
    "token_budget": 10_000,
    "tokens_used": 0,
    "retrieved_chunks": [],
    "web_results": [],
    "memories": [],
    "error": None,
}


def _compile_graph(
    synthesize_spy: Any,
    initial_chunks: list[Any],
    *,
    with_tavily: bool,
) -> Any:
    """Build a test graph with the same topology as the production orchestrator.

    All nodes except synthesize are lightweight stubs — only the topology
    (edges, conditional routing, defer=True) is tested here.
    """

    async def _orchestrator(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
        return {}

    async def _retrieval(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
        return {"retrieved_chunks": initial_chunks}

    async def _memory_read(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
        return {"memories": []}

    async def _web_search(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
        return {"web_results": [{"url": "https://x.com", "title": "X", "content": "y"}]}

    async def _memory_write(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
        return {}

    graph: StateGraph[AgentState] = StateGraph(AgentState)
    graph.add_node("orchestrator", _orchestrator)
    graph.add_node("retrieval", _retrieval)
    graph.add_node("memory_read", _memory_read)
    graph.add_node("web_search", _web_search)
    # defer=True is the fix under test — it tells LangGraph to wait until ALL
    # active predecessor paths complete before firing synthesize.
    graph.add_node("synthesize", synthesize_spy, defer=True)
    graph.add_node("memory_write", _memory_write)

    graph.add_edge(START, "orchestrator")
    graph.add_edge("orchestrator", "retrieval")
    graph.add_edge("orchestrator", "memory_read")
    graph.add_conditional_edges(
        "retrieval",
        _route_after_retrieval,
        {"web_search": "web_search", "synthesize": "synthesize"},
    )
    graph.add_edge("web_search", "synthesize")
    graph.add_edge("memory_read", "synthesize")
    graph.add_edge("synthesize", "memory_write")
    graph.add_edge("memory_write", END)

    compiled = graph.compile()
    return compiled, with_tavily


class TestSynthesizeFiresExactlyOnce:
    async def test_direct_path_no_double_fire(self) -> None:
        """Direct path: retrieval → synthesize AND memory_read → synthesize.
        Two incoming edges → without defer=True, synthesize would fire twice.
        """
        call_count = 0

        async def spy(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            return {}

        enough_chunks = [
            {"chunk_id": str(i), "content": "x"} for i in range(_RETRIEVAL_SUFFICIENT_COUNT)
        ]
        compiled, _ = _compile_graph(spy, enough_chunks, with_tavily=True)

        with patch("app.agents.orchestrator.settings") as mock_s:
            mock_s.TAVILY_API_KEY = "tvly-fake"
            await compiled.ainvoke(dict(_BASE_STATE))

        assert call_count == 1, (
            f"synthesize fired {call_count}× on direct path; "
            "ensure defer=True is set on the synthesize node in build_graph()"
        )

    async def test_web_search_path_no_double_fire(self) -> None:
        """Web-search path: web_search → synthesize AND memory_read → synthesize.
        This is the asymmetric fan-in (1 hop vs 2 hops from orchestrator) that
        originally caused the double-fire: memory_read completes first and fires
        synthesize early; web_search then fires it a second time.
        """
        call_count = 0

        async def spy(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            return {}

        # 0 chunks → routes via web_search (asymmetric fan-in)
        compiled, _ = _compile_graph(spy, initial_chunks=[], with_tavily=True)

        with patch("app.agents.orchestrator.settings") as mock_s:
            mock_s.TAVILY_API_KEY = "tvly-fake"
            await compiled.ainvoke(dict(_BASE_STATE))

        assert call_count == 1, (
            f"synthesize fired {call_count}× on web_search path; "
            "ensure defer=True is set on the synthesize node in build_graph()"
        )

    async def test_no_tavily_path_no_double_fire(self) -> None:
        """Without TAVILY_API_KEY, routing always goes direct — still fires once."""
        call_count = 0

        async def spy(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            return {}

        compiled, _ = _compile_graph(spy, initial_chunks=[], with_tavily=False)

        with patch("app.agents.orchestrator.settings") as mock_s:
            mock_s.TAVILY_API_KEY = ""
            await compiled.ainvoke(dict(_BASE_STATE))

        assert call_count == 1
