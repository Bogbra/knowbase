"""LangGraph StateGraph factory for the Knowbase multi-agent pipeline."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.nodes.memory_read import memory_read_node
from app.agents.nodes.memory_write import memory_write_node
from app.agents.nodes.orchestrate import orchestrator_node
from app.agents.nodes.retrieve import retrieval_node
from app.agents.nodes.synthesize import synthesize_node
from app.agents.nodes.web_search import web_search_node
from app.agents.state import AgentState

_compiled: Any = None


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
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("memory_write", memory_write_node)

    # Fan-out: retrieval, web_search, memory_read run in parallel
    graph.add_edge(START, "orchestrator")
    graph.add_edge("orchestrator", "retrieval")
    graph.add_edge("orchestrator", "web_search")
    graph.add_edge("orchestrator", "memory_read")

    # Fan-in: synthesize waits for all three
    graph.add_edge("retrieval", "synthesize")
    graph.add_edge("web_search", "synthesize")
    graph.add_edge("memory_read", "synthesize")

    graph.add_edge("synthesize", "memory_write")
    graph.add_edge("memory_write", END)

    _compiled = graph.compile()
    return _compiled
