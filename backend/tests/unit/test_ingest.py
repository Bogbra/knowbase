"""Tests for the document ingest ARQ task."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models.document import Document, DocumentStatus


@pytest.fixture
def mock_doc() -> MagicMock:
    doc = MagicMock(spec=Document)
    doc.id = uuid.uuid4()
    doc.s3_key = f"workspaces/ws/{uuid.uuid4()}/file.txt"
    doc.mime_type = "text/plain"
    return doc


@pytest.mark.asyncio
async def test_ingest_marks_ready_on_success(mock_doc: MagicMock) -> None:
    with (
        patch("app.workers.ingest.AsyncSessionLocal") as mock_session_cls,
        patch("app.workers.ingest.download_file", new_callable=AsyncMock) as mock_dl,
        patch("app.workers.ingest.embed_text", new_callable=AsyncMock) as mock_embed,
    ):
        mock_dl.return_value = b"Hello world. This is a test document."
        mock_embed.return_value = [0.0] * 1536

        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_doc
        mock_repo.update_status.return_value = mock_doc

        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = session

        with patch("app.workers.ingest.DocumentRepository", return_value=mock_repo):
            from app.workers.ingest import ingest_document_task

            await ingest_document_task({}, str(mock_doc.id))

        mock_repo.update_status.assert_called_with(mock_doc.id, DocumentStatus.ready)
        session.commit.assert_called()


@pytest.mark.asyncio
async def test_ingest_marks_failed_on_download_error(mock_doc: MagicMock) -> None:
    with (
        patch("app.workers.ingest.AsyncSessionLocal") as mock_session_cls,
        patch(
            "app.workers.ingest.download_file",
            new_callable=AsyncMock,
            side_effect=ConnectionError("S3 unreachable"),
        ),
    ):
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_doc
        mock_repo.update_status.return_value = mock_doc

        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = session

        with patch("app.workers.ingest.DocumentRepository", return_value=mock_repo):
            from app.workers.ingest import ingest_document_task

            with pytest.raises(ConnectionError):
                await ingest_document_task({}, str(mock_doc.id))

        mock_repo.update_status.assert_called_with(mock_doc.id, DocumentStatus.failed)


@pytest.mark.asyncio
async def test_ingest_skips_missing_document() -> None:
    with patch("app.workers.ingest.AsyncSessionLocal") as mock_session_cls:
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None

        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = session

        with patch("app.workers.ingest.DocumentRepository", return_value=mock_repo):
            from app.workers.ingest import ingest_document_task

            await ingest_document_task({}, str(uuid.uuid4()))

        mock_repo.update_status.assert_not_called()


@pytest.mark.asyncio
async def test_ingest_marks_failed_when_no_s3_key() -> None:
    doc = MagicMock(spec=Document)
    doc.id = uuid.uuid4()
    doc.s3_key = None

    with patch("app.workers.ingest.AsyncSessionLocal") as mock_session_cls:
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = doc

        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = session

        with patch("app.workers.ingest.DocumentRepository", return_value=mock_repo):
            from app.workers.ingest import ingest_document_task

            await ingest_document_task({}, str(doc.id))

        mock_repo.update_status.assert_called_with(doc.id, DocumentStatus.failed)
