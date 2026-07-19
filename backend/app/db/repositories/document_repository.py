import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document import Document, DocumentChunk, DocumentStatus


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        result = await self._session.execute(select(Document).where(Document.id == document_id))
        return result.scalar_one_or_none()

    async def get_by_workspace(self, workspace_id: uuid.UUID) -> list[Document]:
        result = await self._session.execute(
            select(Document)
            .where(Document.workspace_id == workspace_id)
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(
        self,
        workspace_id: uuid.UUID,
        name: str,
        mime_type: str | None = None,
        size_bytes: int | None = None,
    ) -> Document:
        document = Document(
            workspace_id=workspace_id,
            name=name,
            status=DocumentStatus.pending,
            mime_type=mime_type,
            size_bytes=size_bytes,
            metadata_={},
        )
        self._session.add(document)
        await self._session.flush()
        await self._session.refresh(document)
        return document

    async def update_status(
        self,
        document_id: uuid.UUID,
        status: DocumentStatus,
        s3_key: str | None = None,
    ) -> Document | None:
        document = await self.get_by_id(document_id)
        if document is None:
            return None
        document.status = status
        if s3_key is not None:
            document.s3_key = s3_key
        await self._session.flush()
        return document

    async def add_chunk(
        self,
        document_id: uuid.UUID,
        content: str,
        chunk_index: int,
        embedding: list[float] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DocumentChunk:
        chunk = DocumentChunk(
            document_id=document_id,
            content=content,
            chunk_index=chunk_index,
            embedding=embedding,
            metadata_=metadata or {},
        )
        self._session.add(chunk)
        await self._session.flush()
        await self._session.refresh(chunk)
        return chunk

    async def get_chunks(self, document_id: uuid.UUID) -> list[DocumentChunk]:
        result = await self._session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        return list(result.scalars().all())

    async def search_similar_chunks(
        self,
        workspace_id: uuid.UUID,
        embedding: list[float],
        limit: int = 10,
    ) -> list[tuple[DocumentChunk, float]]:
        """Return (chunk, cosine_distance) pairs ordered by ascending distance."""
        dist_col = DocumentChunk.embedding.cosine_distance(embedding).label("distance")
        result = await self._session.execute(
            select(DocumentChunk, dist_col)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                Document.workspace_id == workspace_id,
                Document.status == DocumentStatus.ready,
                DocumentChunk.embedding.isnot(None),
            )
            .order_by(dist_col)
            .limit(limit)
        )
        return [(row.DocumentChunk, float(row.distance)) for row in result.all()]
