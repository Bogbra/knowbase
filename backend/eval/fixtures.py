"""Corpus ingestion for eval tests and the CLI runner.

Provides create_eval_workspace() and ingest_corpus() — thin wrappers over
the existing repository layer that bypass storage/ARQ and ingest corpus
text files directly into the database.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.embed import embed_text
from app.core.security import hash_password
from app.db.models.document import Document, DocumentStatus
from app.db.models.user import User, UserRole
from app.db.models.workspace import Workspace, WorkspaceMember, WorkspaceMemberRole
from app.db.repositories.document_repository import DocumentRepository
from app.workers.chunker import split_text_with_metadata

CORPUS_DIR = Path(__file__).parent / "corpus"

# (document_name_in_db, filename_in_corpus_dir)
CORPUS_DOCS: list[tuple[str, str]] = [
    ("Grundlagen des Marketing", "marketing_mix.txt"),
    ("Transaktionskostentheorie", "transaktionskosten.txt"),
    ("Organisationstheorie", "organisationsformen.txt"),
]


async def create_eval_workspace(session: AsyncSession) -> tuple[User, Workspace]:
    """Create a throwaway user and workspace for corpus ingestion in tests."""
    user = User(
        id=uuid.uuid4(),
        email=f"eval-{uuid.uuid4().hex[:8]}@test.local",
        hashed_password=hash_password("EvalPass1!"),
        role=UserRole.user,
        is_active=True,
    )
    session.add(user)
    await session.flush()

    workspace = Workspace(
        id=uuid.uuid4(),
        name=f"Eval Workspace {uuid.uuid4().hex[:6]}",
        owner_id=user.id,
    )
    session.add(workspace)
    await session.flush()

    member = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        user_id=user.id,
        role=WorkspaceMemberRole.owner,
    )
    session.add(member)
    await session.flush()
    return user, workspace


async def ingest_corpus(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    embed: bool = True,
) -> list[Document]:
    """Ingest all corpus documents into workspace_id.

    When embed=False, chunks are stored without embeddings (useful for
    testing chunker behaviour without an OpenAI key).
    """
    repo = DocumentRepository(session)
    documents: list[Document] = []

    for doc_name, filename in CORPUS_DOCS:
        text = (CORPUS_DIR / filename).read_text(encoding="utf-8")

        doc = Document(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            name=doc_name,
            status=DocumentStatus.pending,
            mime_type="text/plain",
            metadata_={},
        )
        session.add(doc)
        await session.flush()

        chunks = split_text_with_metadata(text)
        for i, chunk_data in enumerate(chunks):
            content = str(chunk_data["content"])
            chapter = str(chunk_data.get("chapter") or "")
            embedding: list[float] | None = None
            if embed:
                embedding = await embed_text(content)
            await repo.add_chunk(
                document_id=doc.id,
                content=content,
                chunk_index=i,
                embedding=embedding,
                metadata={"chapter": chapter, "embedding_model": "text-embedding-3-small"}
                if chapter
                else {"embedding_model": "text-embedding-3-small"},
            )

        doc.status = DocumentStatus.ready
        await session.flush()
        documents.append(doc)

    return documents
