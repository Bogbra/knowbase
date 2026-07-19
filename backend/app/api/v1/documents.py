import re
import uuid

from arq.connections import ArqRedis
from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_arq_dep, get_current_user, get_db_dep
from app.core.exceptions import AppError, NotFoundError
from app.core.limiter import limiter
from app.core.storage import delete_file, download_file, upload_file
from app.db.models.document import DocumentStatus
from app.db.models.user import User
from app.db.repositories.document_repository import DocumentRepository
from app.schemas.document import DocumentRead
from app.services.document_service import DocumentService
from app.workers.chunker import is_supported

router = APIRouter(tags=["documents"])

_SAFE_FILENAME = re.compile(r"[^a-zA-Z0-9._\- ]")


def _service(db: AsyncSession = Depends(get_db_dep)) -> DocumentService:
    return DocumentService(db)


@router.get("/workspaces/{workspace_id}/documents", response_model=list[DocumentRead])
async def list_documents(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(_service),
) -> list[DocumentRead]:
    docs = await service.list_by_workspace(workspace_id, current_user.id)
    return [DocumentRead.model_validate(d) for d in docs]


@router.get("/documents/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(_service),
) -> DocumentRead:
    doc = await service.get(document_id, current_user.id)
    return DocumentRead.model_validate(doc)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(_service),
) -> None:
    doc = await service.get(document_id, current_user.id)
    if doc.s3_key:
        await delete_file(doc.s3_key)
    await service.delete(document_id, current_user.id)


@router.post(
    "/workspaces/{workspace_id}/documents/upload",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    workspace_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(_service),
    db: AsyncSession = Depends(get_db_dep),
    arq: ArqRedis = Depends(get_arq_dep),
) -> DocumentRead:
    # Validate size
    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise AppError(
            status_code=413,
            error_type="payload-too-large",
            title="File too large",
            detail=(f"File exceeds the {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB limit"),
        )

    # Validate MIME type
    content_type = (file.content_type or "application/octet-stream").split(";")[0].strip()
    if not is_supported(content_type):
        raise AppError(
            status_code=415,
            error_type="unsupported-media-type",
            title="Unsupported file type",
            detail=f"File type '{content_type}' is not supported",
        )

    # Create DB record (status=pending)
    safe_name = _SAFE_FILENAME.sub("_", file.filename or "document")
    doc = await service.create(
        workspace_id,
        current_user.id,
        safe_name,
        content_type,
        len(data),
    )

    # Upload to storage
    s3_key = f"workspaces/{workspace_id}/documents/{doc.id}/{safe_name}"
    await upload_file(data, s3_key)

    # Update document with s3_key and set status to processing
    doc_repo = DocumentRepository(db)
    updated = await doc_repo.update_status(doc.id, DocumentStatus.processing, s3_key=s3_key)
    await db.commit()

    # Enqueue background ingest job
    await arq.enqueue_job("ingest_document_task", str(doc.id))

    return DocumentRead.model_validate(updated or doc)


@router.post("/documents/{document_id}/requeue", response_model=DocumentRead)
@limiter.limit("5/minute")
async def requeue_document(
    request: Request,
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(_service),
    db: AsyncSession = Depends(get_db_dep),
    arq: ArqRedis = Depends(get_arq_dep),
) -> DocumentRead:
    doc = await service.get(document_id, current_user.id)
    if doc.status not in (DocumentStatus.failed, DocumentStatus.pending):
        raise AppError(
            status_code=409,
            error_type="conflict",
            title="Cannot requeue",
            detail=f"Document status '{doc.status}' cannot be requeued",
        )
    doc_repo = DocumentRepository(db)
    updated = await doc_repo.update_status(document_id, DocumentStatus.processing)
    await db.commit()
    await arq.enqueue_job("ingest_document_task", str(document_id))
    return DocumentRead.model_validate(updated or doc)


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: DocumentService = Depends(_service),
) -> Response:
    doc = await service.get(document_id, current_user.id)
    if not doc.s3_key:
        raise NotFoundError("Document file", str(document_id))

    data = await download_file(doc.s3_key)
    return Response(
        content=data,
        media_type=doc.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{doc.name}"'},
    )
