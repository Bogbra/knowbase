"""Web search tool — Tavily-backed, returns top-k results as structured dicts."""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class SearchResult:
    __slots__ = ("title", "url", "content", "score")

    def __init__(self, title: str, url: str, content: str, score: float) -> None:
        self.title = title
        self.url = url
        self.content = content
        self.score = score

    def as_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "score": self.score,
        }


async def web_search(query: str, k: int = 5) -> list[dict[str, Any]]:
    """Run a Tavily web search and return up to *k* results.

    Returns an empty list (instead of raising) when the API key is absent or
    the request fails — callers should treat an empty list as "no results".
    """
    if not settings.TAVILY_API_KEY:
        logger.warning("web_search_skipped: TAVILY_API_KEY not set")
        return []

    try:
        from tavily import AsyncTavilyClient

        client = AsyncTavilyClient(api_key=settings.TAVILY_API_KEY)
        response: dict[str, Any] = await client.search(
            query=query,
            max_results=k,
            search_depth="basic",
            include_answer=False,
        )
        results: list[dict[str, Any]] = response.get("results", [])
        return [
            SearchResult(
                title=str(r.get("title", "")),
                url=str(r.get("url", "")),
                content=str(r.get("content", ""))[:1500],
                score=float(r.get("score", 0.0)),
            ).as_dict()
            for r in results[:k]
        ]
    except Exception:
        logger.exception("web_search_failed query=%r", query)
        return []
