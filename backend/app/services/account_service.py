"""Account self-service: deletion and data export.

Deletion — three-case workspace rule (see delete_account docstring).
Export — all user-generated data as a portable JSON structure (GDPR Art. 20).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, InvalidCredentialsError
from app.core.security import verify_password
from app.db.models.user import User
from app.db.models.workspace import WorkspaceMemberRole
from app.db.repositories.api_key_repository import ApiKeyRepository
from app.db.repositories.conversation_repository import ConversationRepository
from app.db.repositories.document_repository import DocumentRepository
from app.db.repositories.memory_repository import MemoryRepository
from app.db.repositories.message_repository import MessageRepository
from app.db.repositories.workspace_repository import WorkspaceRepository
from app.schemas.account import (
    ExportApiKey,
    ExportConversation,
    ExportDocument,
    ExportMemory,
    ExportMessage,
    ExportProfile,
    ExportResponse,
    ExportWorkspace,
)

logger = logging.getLogger(__name__)


class AccountService:
    def __init__(self, db: AsyncSession, redis: aioredis.Redis) -> None:
        self._db = db
        self._redis = redis

    async def delete_account(self, user: User, password: str) -> list[str]:
        """Delete the account applying the three-case workspace rule.

        Case 1 — sole member of a workspace: workspace deleted (DB cascade removes
          documents, chunks, conversations, messages, memories, tasks, agent_runs).
        Case 2 — non-owner member of a shared workspace: membership removed; workspace
          and all other members' data are unaffected.
        Case 3 — owner of a shared workspace (other members present): raises
          ConflictError(409). Caller must transfer ownership or delete the workspace
          first. Ownership transfer is not built here to avoid scope creep.

        Redis event-streams (sse:run:{id}) are NOT cleaned up on deletion. They carry
        a TTL and expire within 1 h — the risk window is acceptable and documented as
        a conscious decision (scanning all Redis keys on every account delete would be
        disproportionate).

        Returns a list of S3 keys whose files should be deleted after the DB transaction
        commits. Caller is responsible for the best-effort S3 cleanup loop.
        """
        if not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()

        ws_repo = WorkspaceRepository(self._db)
        doc_repo = DocumentRepository(self._db)

        memberships = await ws_repo.get_memberships_for_user(user.id)
        s3_keys: list[str] = []

        for membership in memberships:
            members = await ws_repo.get_members(membership.workspace_id)
            is_sole_member = len(members) == 1

            if is_sole_member:
                docs = await doc_repo.get_by_workspace(membership.workspace_id)
                s3_keys.extend(d.s3_key for d in docs if d.s3_key)
                workspace = await ws_repo.get_by_id(membership.workspace_id)
                if workspace is not None:
                    await self._db.delete(workspace)
            elif membership.role == WorkspaceMemberRole.owner:
                workspace = await ws_repo.get_by_id(membership.workspace_id)
                name = workspace.name if workspace else str(membership.workspace_id)
                raise ConflictError(
                    f"Transfer ownership of workspace '{name}' or delete it "
                    "before deleting your account."
                )
            else:
                await self._db.delete(membership)

        await self._db.flush()
        await self._invalidate_refresh_tokens(str(user.id))
        await self._db.delete(user)
        logger.info("account_deleted", extra={"user_id": str(user.id)})
        return s3_keys

    async def export_account(self, user: User) -> ExportResponse:
        """Collect all user-generated data for GDPR data portability (Art. 20).

        Documents are exported as metadata only (name, status, mime_type, size) — not
        file contents. Files were uploaded by the user; presigned URLs here would be
        scope creep and add time-limited coupling to the export artifact.

        API key metadata (name, created_at, last_used_at) is included. key_hash is
        never exported.
        """
        ws_repo = WorkspaceRepository(self._db)
        conv_repo = ConversationRepository(self._db)
        msg_repo = MessageRepository(self._db)
        mem_repo = MemoryRepository(self._db)
        doc_repo = DocumentRepository(self._db)
        key_repo = ApiKeyRepository(self._db)

        memberships = await ws_repo.get_memberships_for_user(user.id)

        export_workspaces: list[ExportWorkspace] = []
        export_docs: list[ExportDocument] = []
        seen_doc_ids: set[uuid.UUID] = set()

        for membership in memberships:
            workspace = await ws_repo.get_by_id(membership.workspace_id)
            if workspace is None:
                continue
            export_workspaces.append(
                ExportWorkspace(id=workspace.id, name=workspace.name, role=membership.role)
            )
            for doc in await doc_repo.get_by_workspace(membership.workspace_id):
                if doc.id not in seen_doc_ids:
                    seen_doc_ids.add(doc.id)
                    export_docs.append(ExportDocument.model_validate(doc))

        export_convs: list[ExportConversation] = []
        for conv in await conv_repo.get_by_user(user.id):
            messages = await msg_repo.get_by_conversation(conv.id)
            export_convs.append(
                ExportConversation(
                    id=conv.id,
                    title=conv.title,
                    workspace_id=conv.workspace_id,
                    created_at=conv.created_at,
                    messages=[ExportMessage.model_validate(m) for m in messages],
                )
            )

        return ExportResponse(
            exported_at=datetime.now(UTC),
            profile=ExportProfile.model_validate(user),
            workspaces=export_workspaces,
            conversations=export_convs,
            memories=[ExportMemory.model_validate(m) for m in await mem_repo.get_by_user(user.id)],
            documents=export_docs,
            api_keys=[
                ExportApiKey.model_validate(k) for k in await key_repo.list_for_user(user.id)
            ],
        )

    async def _invalidate_refresh_tokens(self, user_id: str) -> None:
        """Scan Redis for refresh tokens belonging to user_id and delete them."""
        cursor = 0
        while True:
            cursor, keys = await self._redis.scan(cursor, match="refresh:*", count=100)
            for key in keys:
                value = await self._redis.get(key)
                if value and value.decode() == user_id:
                    await self._redis.delete(key)
            if cursor == 0:
                break
