"""API key management — create, list, and revoke personal access tokens.

Keys are scoped to a single workspace and intended for machine-to-machine access
(MCP servers, scripts). The raw key is shown exactly once on creation.
"""

import hashlib
import secrets
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_dep
from app.core.exceptions import NotFoundError
from app.db.models.user import User
from app.db.repositories.api_key_repository import ApiKeyRepository
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyRead
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/auth/api-keys", tags=["api-keys"])

_KEY_PREFIX = "kb_"
_KEY_BYTES = 32  # 256 bits of entropy → 64 hex chars


def _make_raw_key() -> str:
    return _KEY_PREFIX + secrets.token_hex(_KEY_BYTES)


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _repo(db: AsyncSession = Depends(get_db_dep)) -> ApiKeyRepository:
    return ApiKeyRepository(db)


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    body: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_dep),
    repo: ApiKeyRepository = Depends(_repo),
) -> ApiKeyCreated:
    """Create a workspace-scoped API key. The raw key is shown once — store it securely."""
    # Verify caller is a member of the target workspace
    ws_service = WorkspaceService(db)
    await ws_service.get(body.workspace_id, current_user.id)  # raises NotFoundError if not member

    raw = _make_raw_key()
    api_key = await repo.create(
        user_id=current_user.id,
        workspace_id=body.workspace_id,
        name=body.name,
        key_hash=_hash_key(raw),
    )
    await db.commit()

    return ApiKeyCreated(
        id=api_key.id,
        name=api_key.name,
        workspace_id=api_key.workspace_id,
        created_at=api_key.created_at,
        key=raw,
    )


@router.get("", response_model=list[ApiKeyRead])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    repo: ApiKeyRepository = Depends(_repo),
) -> list[ApiKeyRead]:
    """List all active API keys for the current user."""
    keys = await repo.list_for_user(current_user.id)
    return [ApiKeyRead.model_validate(k) for k in keys]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_dep),
    repo: ApiKeyRepository = Depends(_repo),
) -> None:
    """Revoke an API key. Immediate effect — any in-flight requests using this key will fail."""
    ok = await repo.revoke(key_id, current_user.id)
    if not ok:
        raise NotFoundError("API key", str(key_id))
    await db.commit()
