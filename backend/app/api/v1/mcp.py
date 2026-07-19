"""MCP endpoints — machine-to-machine access via API key (no JWT).

Three read-only tools mirroring the MCP server tools:
  POST /mcp/search              embed query + vector search
  GET  /mcp/documents           list workspace documents
  GET  /mcp/documents/{id}      document metadata

All endpoints require an API key (Authorization: Bearer kb_<hex>).
The workspace is derived from the key — callers cannot access other workspaces.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.embed import embed_text
from app.agents.tools.vector_search import vector_search
from app.core.deps import get_db_dep
from app.core.limiter import limiter
from app.db.models.document import DocumentStatus
from app.db.models.user import User
from app.db.repositories.api_key_repository import ApiKeyRepository
from app.db.repositories.document_repository import DocumentRepository
from app.db.repositories.user_repository import UserRepository
from app.schemas.api_key import ChunkResult, SearchRequest, SearchResponse
from app.schemas.document import DocumentRead

router = APIRouter(prefix="/mcp", tags=["mcp"])

_bearer = HTTPBearer(auto_error=True)


@dataclass(frozen=True)
class _ApiKeyContext:
    user: User
    workspace_id: uuid.UUID


async def _resolve_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db_dep),
) -> _ApiKeyContext:
    token = credentials.credentials
    if not token.startswith("kb_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required — must start with 'kb_'",
        )

    key_hash = hashlib.sha256(token.encode()).hexdigest()
    api_key_repo = ApiKeyRepository(db)
    api_key = await api_key_repo.get_by_hash(key_hash)
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    user = await UserRepository(db).get_by_id(api_key.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="API key user not found"
        )

    # Fire-and-forget last_used_at update (best-effort, no commit needed here)
    await api_key_repo.touch(api_key.id)

    return _ApiKeyContext(user=user, workspace_id=api_key.workspace_id)


@router.post("/search", response_model=SearchResponse)
@limiter.limit("20/minute")
async def mcp_search(
    request: Request,
    body: SearchRequest,
    ctx: _ApiKeyContext = Depends(_resolve_api_key),
    db: AsyncSession = Depends(get_db_dep),
) -> SearchResponse:
    """Semantic search over the workspace knowledge base.

    Returns the top-k most relevant chunks, ranked by cosine distance.
    Intended for use by the Knowbase MCP server tool search_knowledge().
    """
    embedding = await embed_text(body.query)
    results = await vector_search(
        query_embedding=embedding,
        workspace_id=str(ctx.workspace_id),
        session=db,
        k=body.k,
    )

    doc_repo = DocumentRepository(db)
    docs = await doc_repo.get_by_workspace(ctx.workspace_id)
    name_map = {str(d.id): d.name for d in docs}

    chunks: list[ChunkResult] = []
    for r in results:
        doc_name = name_map.get(r.document_id, "Unknown")
        chapter = str(r.metadata.get("chapter", "")).strip()
        source_label = f"{doc_name}, {chapter}" if chapter else doc_name
        chunks.append(
            ChunkResult(
                document_id=r.document_id,
                document_name=doc_name,
                chapter=chapter,
                content=r.content,
                distance=round(r.score, 4),
                source_label=source_label,
            )
        )

    return SearchResponse(chunks=chunks, query=body.query, total=len(chunks))


@router.get("/documents", response_model=list[DocumentRead])
@limiter.limit("60/minute")
async def mcp_list_documents(
    request: Request,
    ctx: _ApiKeyContext = Depends(_resolve_api_key),
    db: AsyncSession = Depends(get_db_dep),
) -> list[DocumentRead]:
    """List all ready documents in the API key's workspace."""
    repo = DocumentRepository(db)
    docs = await repo.get_by_workspace(ctx.workspace_id)
    ready = [d for d in docs if d.status == DocumentStatus.ready]
    return [DocumentRead.model_validate(d) for d in ready]


@router.get("/documents/{document_id}", response_model=DocumentRead)
@limiter.limit("60/minute")
async def mcp_get_document(
    request: Request,
    document_id: uuid.UUID,
    ctx: _ApiKeyContext = Depends(_resolve_api_key),
    db: AsyncSession = Depends(get_db_dep),
) -> DocumentRead:
    """Get metadata for a specific document (must belong to the API key's workspace)."""
    repo = DocumentRepository(db)
    doc = await repo.get_by_id(document_id)
    if doc is None or doc.workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentRead.model_validate(doc)
