import uuid
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ForbiddenError
from app.core.redis import get_redis
from app.core.security import decode_token
from app.db.models.user import User, UserRole
from app.db.repositories.user_repository import UserRepository
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

_arq_pool: ArqRedis | None = None


async def get_arq_dep() -> AsyncGenerator[ArqRedis, None]:
    global _arq_pool
    if _arq_pool is None:
        _arq_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    yield _arq_pool


async def get_db_dep() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db():
        yield session


async def get_redis_dep() -> AsyncGenerator[aioredis.Redis, None]:
    async for client in get_redis():
        yield client


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_dep),
) -> User:
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    sub: str | None = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    try:
        user_id = uuid.UUID(sub)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc

    user = await UserRepository(db).get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise ForbiddenError("Admin access required")
    return current_user
