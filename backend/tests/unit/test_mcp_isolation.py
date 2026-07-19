"""Workspace-isolation tests for MCP endpoints.

Verifies that a key issued for workspace A cannot read data from workspace B,
even if a caller crafts a request with a valid B document ID.

SlowAPI wraps handlers with @functools.wraps, so __wrapped__ gives direct
access to the original async function — no Redis, no isinstance(request) checks.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.mcp import _ApiKeyContext, mcp_get_document, mcp_search
from app.db.repositories.document_repository import DocumentRepository

# Unwrap SlowAPI decoration to test logic without Redis or Starlette Request.
_get_document = mcp_get_document.__wrapped__
_search = mcp_search.__wrapped__


def _ctx(workspace_id: uuid.UUID) -> _ApiKeyContext:
    return _ApiKeyContext(user=MagicMock(), workspace_id=workspace_id)


def _mock_db() -> AsyncMock:
    return AsyncMock()


class TestGetDocumentWorkspaceIsolation:
    async def test_cross_workspace_document_returns_404(self) -> None:
        """Key from workspace A must not expose a document belonging to workspace B."""
        workspace_a = uuid.uuid4()
        workspace_b = uuid.uuid4()

        doc = MagicMock()
        doc.workspace_id = workspace_b

        mock_repo = AsyncMock(spec=DocumentRepository)
        mock_repo.get_by_id.return_value = doc

        with patch("app.api.v1.mcp.DocumentRepository", return_value=mock_repo):
            with pytest.raises(HTTPException) as exc_info:
                await _get_document(
                    request=MagicMock(),
                    document_id=uuid.uuid4(),
                    ctx=_ctx(workspace_a),
                    db=_mock_db(),
                )

        assert exc_info.value.status_code == 404

    async def test_same_workspace_document_succeeds(self) -> None:
        """Key from workspace A can read a document belonging to workspace A."""
        workspace_a = uuid.uuid4()

        doc = MagicMock()
        doc.workspace_id = workspace_a

        mock_repo = AsyncMock(spec=DocumentRepository)
        mock_repo.get_by_id.return_value = doc

        with patch("app.api.v1.mcp.DocumentRepository", return_value=mock_repo):
            with patch("app.api.v1.mcp.DocumentRead.model_validate", return_value=MagicMock()):
                result = await _get_document(
                    request=MagicMock(),
                    document_id=uuid.uuid4(),
                    ctx=_ctx(workspace_a),
                    db=_mock_db(),
                )

        assert result is not None

    async def test_nonexistent_document_returns_404(self) -> None:
        """A missing document ID must return 404, not 500."""
        mock_repo = AsyncMock(spec=DocumentRepository)
        mock_repo.get_by_id.return_value = None

        with patch("app.api.v1.mcp.DocumentRepository", return_value=mock_repo):
            with pytest.raises(HTTPException) as exc_info:
                await _get_document(
                    request=MagicMock(),
                    document_id=uuid.uuid4(),
                    ctx=_ctx(uuid.uuid4()),
                    db=_mock_db(),
                )

        assert exc_info.value.status_code == 404


class TestSearchWorkspaceIsolation:
    async def test_search_uses_key_workspace_not_request_body(self) -> None:
        """vector_search must receive workspace_id from the key context, not from
        the client — SearchRequest contains only query/k, no workspace_id field."""
        workspace_id = uuid.uuid4()

        mock_repo = AsyncMock(spec=DocumentRepository)
        mock_repo.get_by_workspace.return_value = []

        with (
            patch("app.api.v1.mcp.embed_text", new=AsyncMock(return_value=[0.1] * 1536)),
            patch("app.api.v1.mcp.vector_search", new=AsyncMock(return_value=[])) as vs_mock,
            patch("app.api.v1.mcp.DocumentRepository", return_value=mock_repo),
        ):
            from app.schemas.api_key import SearchRequest

            await _search(
                request=MagicMock(),
                body=SearchRequest(query="test", k=5),
                ctx=_ctx(workspace_id),
                db=_mock_db(),
            )

        assert vs_mock.call_args.kwargs["workspace_id"] == str(workspace_id)
