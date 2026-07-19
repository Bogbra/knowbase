"""LangGraph StateGraph factory for the Knowbase RAG pipeline.

Graph shape:
  orchestrator
    ├─ retrieval ──(conditional)──► web_search ──┐
    │                         └───► synthesize ◄─┤
    └─ memory_read ───────────────────────────────┘
         synthesize ► memory_write ► END

web_search runs only when TAVILY_API_KEY is configured AND retrieval returns
fewer than 3 chunks above the relevance threshold.
"""

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from app.agents.nodes.memory_read import memory_read_node
from app.agents.nodes.memory_write import memory_write_node
from app.agents.nodes.orchestrate import orchestrator_node
from app.agents.nodes.retrieve import retrieval_node
from app.agents.nodes.synthesize import synthesize_node
from app.agents.nodes.web_search import web_search_node
from app.agents.state import AgentState
from app.core.config import settings

_compiled: Any = None

_RETRIEVAL_SUFFICIENT_COUNT = 3


def _route_after_retrieval(state: AgentState) -> Literal["web_search", "synthesize"]:
    """Route to web_search only when retrieval results are insufficient.

    vector_search already applies the distance threshold, so all chunks in
    retrieved_chunks are below it. The count alone determines sufficiency.
    """
    if not settings.TAVILY_API_KEY:
        return "synthesize"
    if len(state.get("retrieved_chunks", [])) < _RETRIEVAL_SUFFICIENT_COUNT:
        return "web_search"
    return "synthesize"


def build_graph() -> Any:
    """Return the compiled agent graph (singleton, built on first call)."""
    global _compiled
    if _compiled is not None:
        return _compiled

    graph: StateGraph[AgentState] = StateGraph(AgentState)

    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("web_search", web_search_node)
    graph.add_node("memory_read", memory_read_node)
    # defer=True: synthesize waits until ALL active predecessor paths complete
    # before firing. Without it, the asymmetric fan-in (memory_read is 1 hop,
    # web_search is 2 hops from orchestrator) causes synthesize to fire twice
    # when the fallback path runs — once without web results, once with.
    graph.add_node("synthesize", synthesize_node, defer=True)
    graph.add_node("memory_write", memory_write_node)

    graph.add_edge(START, "orchestrator")
    # retrieval and memory_read run in parallel after orchestrator
    graph.add_edge("orchestrator", "retrieval")
    graph.add_edge("orchestrator", "memory_read")

    # web_search is a conditional fallback — only runs when retrieval is insufficient
    graph.add_conditional_edges(
        "retrieval",
        _route_after_retrieval,
        {"web_search": "web_search", "synthesize": "synthesize"},
    )
    graph.add_edge("web_search", "synthesize")
    graph.add_edge("memory_read", "synthesize")

    graph.add_edge("synthesize", "memory_write")
    graph.add_edge("memory_write", END)

    _compiled = graph.compile()
    return _compiled
