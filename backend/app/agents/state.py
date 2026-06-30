from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    conversation_id: str
    workspace_id: str
    user_id: str
    run_id: str
    stream_key: str
    token_budget: int
    tokens_used: int
    retrieved_chunks: list[dict[str, Any]]
    web_results: list[dict[str, Any]]
    memories: list[dict[str, Any]]
    error: str | None
