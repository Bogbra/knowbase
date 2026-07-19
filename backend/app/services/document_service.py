import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.models.document import Document
from app.db.repositories.document_repository import DocumentRepository
from app.db.repositories.workspace_repository import WorkspaceRepository


class DocumentService:
    def __init__(self, session: AsyncSession) -> None:
        self._doc_repo = DocumentRepository(session)
        self._ws_repo = WorkspaceRepository(session)

    async def _check_workspace_access(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> None:
        workspace = await self._ws_repo.get_by_id(workspace_id)
        if workspace is None:
            raise NotFoundError("Workspace", str(workspace_id))
        member = await self._ws_repo.get_member(workspace_id, user_id)
        if member is None:
            raise ForbiddenError("Not a member of this workspace")

    async def create(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        name: str,
        mime_type: str | None = None,
        size_bytes: int | None = None,
    ) -> Document:
        await self._check_workspace_access(workspace_id, user_id)
        return await self._doc_repo.create(workspace_id, name, mime_type, size_bytes)

    async def list_by_workspace(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[Document]:
        await self._check_workspace_access(workspace_id, user_id)
        return await self._doc_repo.get_by_workspace(workspace_id)

    async def get(self, document_id: uuid.UUID, user_id: uuid.UUID) -> Document:
        doc = await self._doc_repo.get_by_id(document_id)
        if doc is None:
            raise NotFoundError("Document", str(document_id))
        await self._check_workspace_access(doc.workspace_id, user_id)
        return doc

    async def delete(self, document_id: uuid.UUID, user_id: uuid.UUID) -> None:
        doc = await self.get(document_id, user_id)
        await self._doc_repo._session.delete(doc)
