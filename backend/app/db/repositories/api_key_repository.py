import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.api_key import ApiKey


class ApiKeyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        name: str,
        key_hash: str,
    ) -> ApiKey:
        key = ApiKey(
            id=uuid.uuid4(),
            user_id=user_id,
            workspace_id=workspace_id,
            name=name,
            key_hash=key_hash,
        )
        self._session.add(key)
        await self._session.flush()
        await self._session.refresh(key)
        return key

    async def get_by_hash(self, key_hash: str) -> ApiKey | None:
        # A plain equality lookup is intentional here, not an oversight: key_hash
        # is a SHA-256 digest of a 256-bit random token (see api_key.py), so unlike
        # a password hash there is no low-entropy secret to protect against offline
        # guessing — the digest itself carries no exploitable timing signal, and
        # the column is indexed (unique=True, index=True) so this stays O(1).
        result = await self._session.execute(
            select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID) -> list[ApiKey]:
        result = await self._session.execute(
            select(ApiKey)
            .where(ApiKey.user_id == user_id, ApiKey.is_active.is_(True))
            .order_by(ApiKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def revoke(self, key_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        result = await self._session.execute(
            update(ApiKey)
            .where(ApiKey.id == key_id, ApiKey.user_id == user_id)
            .values(is_active=False)
        )
        return bool(result.rowcount)  # type: ignore[attr-defined]

    async def touch(self, key_id: uuid.UUID) -> None:
        await self._session.execute(
            update(ApiKey).where(ApiKey.id == key_id).values(last_used_at=datetime.now(UTC))
        )
