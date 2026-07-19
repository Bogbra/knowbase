"""Unit tests for MCP tools — client is mocked, no HTTP calls made."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

import app.main as main_module
from app.main import get_document, list_documents, search_knowledge


@pytest.fixture(autouse=True)
def mock_client(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    client = MagicMock()
    client.search = AsyncMock()
    client.list_documents = AsyncMock()
    client.get_document = AsyncMock()
    monkeypatch.setattr(main_module, "_client", client)
    return client


class TestSearchKnowledge:
    async def test_returns_formatted_chunks(self, mock_client: MagicMock) -> None:
        mock_client.search.return_value = [
            {
                "source_label": "Grundlagen des Marketing, 1 Marketing-Mix",
                "distance": 0.12,
                "content": "Der Marketing-Mix umfasst vier Instrumente.",
            }
        ]

        result = await search_knowledge("Was ist der Marketing-Mix?", 8)

        assert "Found 1 relevant chunk" in result
        assert "Grundlagen des Marketing, 1 Marketing-Mix" in result
        assert "0.12" in result
        assert "Der Marketing-Mix umfasst vier Instrumente." in result
        mock_client.search.assert_awaited_once_with("Was ist der Marketing-Mix?", 8)

    async def test_no_results_returns_not_found_message(self, mock_client: MagicMock) -> None:
        mock_client.search.return_value = []

        result = await search_knowledge("Unbekanntes Thema", 8)

        assert "No relevant information found" in result

    async def test_multiple_chunks_numbered(self, mock_client: MagicMock) -> None:
        mock_client.search.return_value = [
            {"source_label": "Doc A", "distance": 0.1, "content": "Inhalt A"},
            {"source_label": "Doc B", "distance": 0.2, "content": "Inhalt B"},
        ]

        result = await search_knowledge("test", 2)

        assert "[1]" in result
        assert "[2]" in result


class TestListDocuments:
    async def test_returns_document_list(self, mock_client: MagicMock) -> None:
        mock_client.list_documents.return_value = [
            {"name": "Grundlagen des Marketing", "id": "abc-123"},
            {"name": "Transaktionskostentheorie", "id": "def-456"},
        ]

        result = await list_documents()

        assert "2 document(s)" in result
        assert "Grundlagen des Marketing" in result
        assert "abc-123" in result
        assert "Transaktionskostentheorie" in result

    async def test_empty_workspace(self, mock_client: MagicMock) -> None:
        mock_client.list_documents.return_value = []

        result = await list_documents()

        assert "No documents found" in result


class TestGetDocument:
    async def test_returns_formatted_metadata(self, mock_client: MagicMock) -> None:
        mock_client.get_document.return_value = {
            "name": "Grundlagen des Marketing",
            "id": "abc-123",
            "status": "ready",
            "mime_type": "application/pdf",
        }

        result = await get_document("abc-123")

        assert "Grundlagen des Marketing" in result
        assert "abc-123" in result
        assert "ready" in result
        assert "application/pdf" in result
        mock_client.get_document.assert_awaited_once_with("abc-123")

    async def test_missing_mime_type_shows_unknown(self, mock_client: MagicMock) -> None:
        mock_client.get_document.return_value = {
            "name": "Doc",
            "id": "x",
            "status": "ready",
        }

        result = await get_document("x")

        assert "unknown" in result
