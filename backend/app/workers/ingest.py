"""ARQ task: download → extract → chunk → embed → persist document content."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from app.agents.embed import embed_text
from app.core.metrics import document_ingests_total
from app.core.storage import download_file
from app.db.models.document import DocumentStatus
from app.db.repositories.document_repository import DocumentRepository
from app.db.session import AsyncSessionLocal
from app.workers.chunker import extract_text, split_text_with_metadata

logger = logging.getLogger(__name__)


async def ingest_document_task(
    ctx: dict[str, Any],
    document_id: str,
) -> None:
    """Process a document: download from storage, chunk, embed, and save to DB.

    Marks the document as DocumentStatus.ready on success or DocumentStatus.failed
    on any unrecoverable error.
    """
    doc_uuid = uuid.UUID(document_id)

    async with AsyncSessionLocal() as session:
        repo = DocumentRepository(session)
        doc = await repo.get_by_id(doc_uuid)

        if doc is None:
            logger.error("Document not found", extra={"document_id": document_id})
            return

        if not doc.s3_key:
            logger.error("Document missing s3_key", extra={"document_id": document_id})
            await repo.update_status(doc_uuid, DocumentStatus.failed)
            await session.commit()
            return

        document_ingests_total.labels(status="started").inc()
        try:
            file_bytes = await download_file(doc.s3_key)
            text = extract_text(file_bytes, doc.mime_type or "text/plain")
            chunk_dicts = split_text_with_metadata(text)

            if not chunk_dicts:
                logger.warning(
                    "No text extracted from document",
                    extra={"document_id": document_id},
                )

            for i, chunk in enumerate(chunk_dicts):
                if i > 0:
                    await asyncio.sleep(0.5)  # throttle to ~2 req/s — proxy rate limit
                chunk_text = str(chunk["content"])
                chapter = str(chunk.get("chapter") or "")
                embedding = await embed_text(chunk_text)
                await repo.add_chunk(
                    document_id=doc_uuid,
                    content=chunk_text,
                    chunk_index=i,
                    embedding=embedding,
                    metadata={"chapter": chapter} if chapter else {},
                )

            await repo.update_status(doc_uuid, DocumentStatus.ready)
            await session.commit()
            document_ingests_total.labels(status="completed").inc()
            logger.info(
                "Document ingested",
                extra={"document_id": document_id, "chunks": len(chunk_dicts)},
            )

        except Exception:
            document_ingests_total.labels(status="failed").inc()
            logger.exception("Document ingest failed", extra={"document_id": document_id})
            try:
                await repo.update_status(doc_uuid, DocumentStatus.failed)
                await session.commit()
            except Exception:
                logger.exception("Failed to mark document as failed")
            raise
