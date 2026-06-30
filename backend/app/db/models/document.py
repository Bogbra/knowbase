import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DocumentStatus(StrEnum):
    pending = "pending"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="documentstatus"),
        nullable=False,
        default=DocumentStatus.pending,
    )
    s3_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
    )
