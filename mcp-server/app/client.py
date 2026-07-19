"""Thin async HTTP client for the Knowbase MCP REST endpoints.

Keeps all HTTP logic in one place so tools stay clean and tests can
inject a mock client without patching httpx internals.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings


class KnowbaseClient:
    def __init__(self, settings: Settings) -> None:
        self._base = settings.KNOWBASE_API_URL.rstrip("/")
        self._headers = {"Authorization": f"Bearer {settings.KNOWBASE_API_KEY}"}

    async def search(self, query: str, k: int = 8) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as http:
            r = await http.post(
                f"{self._base}/api/v1/mcp/search",
                json={"query": query, "k": k},
                headers=self._headers,
            )
            r.raise_for_status()
            return r.json()["chunks"]  # type: ignore[no-any-return]

    async def list_documents(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=10.0) as http:
            r = await http.get(
                f"{self._base}/api/v1/mcp/documents",
                headers=self._headers,
            )
            r.raise_for_status()
            return r.json()  # type: ignore[no-any-return]

    async def get_document(self, document_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as http:
            r = await http.get(
                f"{self._base}/api/v1/mcp/documents/{document_id}",
                headers=self._headers,
            )
            r.raise_for_status()
            return r.json()  # type: ignore[no-any-return]
