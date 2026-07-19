import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models.document import Document, DocumentStatus
from app.db.repositories.document_repository import DocumentRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def repo(mock_session: AsyncMock) -> DocumentRepository:
    return DocumentRepository(mock_session)


class TestCreate:
    async def test_creates_document_with_required_fields(
        self, repo: DocumentRepository, mock_session: AsyncMock
    ) -> None:
        workspace_id = uuid.uuid4()

        await repo.create(workspace_id, "report.pdf", mime_type="application/pdf", size_bytes=1024)

        mock_session.add.assert_called_once()
        doc = mock_session.add.call_args[0][0]
        assert isinstance(doc, Document)
        assert doc.workspace_id == workspace_id
        assert doc.name == "report.pdf"
        assert doc.mime_type == "application/pdf"
        assert doc.size_bytes == 1024
        assert doc.status == DocumentStatus.pending

    async def test_creates_document_with_defaults(
        self, repo: DocumentRepository, mock_session: AsyncMock
    ) -> None:
        await repo.create(uuid.uuid4(), "notes.txt")

        doc = mock_session.add.call_args[0][0]
        assert doc.mime_type is None
        assert doc.size_bytes is None


class TestGetById:
    async def test_returns_document(
        self, repo: DocumentRepository, mock_session: AsyncMock
    ) -> None:
        expected = MagicMock(spec=Document)
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = expected
        mock_session.execute.return_value = execute_result

        result = await repo.get_by_id(uuid.uuid4())

        assert result is expected

    async def test_returns_none_when_missing(
        self, repo: DocumentRepository, mock_session: AsyncMock
    ) -> None:
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = execute_result

        result = await repo.get_by_id(uuid.uuid4())

        assert result is None


class TestUpdateStatus:
    async def test_updates_status_and_s3_key(
        self, repo: DocumentRepository, mock_session: AsyncMock
    ) -> None:
        doc = MagicMock(spec=Document)
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = doc
        mock_session.execute.return_value = execute_result

        result = await repo.update_status(
            uuid.uuid4(), DocumentStatus.ready, s3_key="bucket/key.pdf"
        )

        assert result is doc
        assert doc.status == DocumentStatus.ready
        assert doc.s3_key == "bucket/key.pdf"

    async def test_returns_none_when_document_missing(
        self, repo: DocumentRepository, mock_session: AsyncMock
    ) -> None:
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = execute_result

        result = await repo.update_status(uuid.uuid4(), DocumentStatus.failed)

        assert result is None
