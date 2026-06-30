import logging

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserInactiveError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models.user import User
from app.db.repositories.user_repository import UserRepository
from app.schemas.auth import TokenResponse
from app.schemas.user import UserResponse

logger = logging.getLogger(__name__)

_REFRESH_TTL = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        redis: aioredis.Redis,
    ) -> None:
        self._repo = user_repo
        self._redis = redis

    async def register(self, email: str, password: str) -> tuple[UserResponse, TokenResponse]:
        if await self._repo.get_by_email(email) is not None:
            raise EmailAlreadyExistsError(email)

        hashed = hash_password(password)
        user = await self._repo.create(email=email, hashed_password=hashed)
        tokens = await self._issue_tokens(str(user.id))

        logger.info("user_registered", extra={"user_id": str(user.id)})
        return UserResponse.model_validate(user), tokens

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self._repo.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()
        if not user.is_active:
            raise UserInactiveError()

        tokens = await self._issue_tokens(str(user.id))
        logger.info("user_logged_in", extra={"user_id": str(user.id)})
        return tokens

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
        except ValueError as exc:
            raise InvalidTokenError() from exc

        if payload.get("type") != "refresh":
            raise InvalidTokenError()

        jti: str | None = payload.get("jti")
        user_id: str | None = payload.get("sub")

        if not jti or not user_id:
            raise InvalidTokenError()

        stored = await self._redis.get(f"refresh:{jti}")
        if stored is None or stored.decode() != user_id:
            raise InvalidTokenError()

        await self._redis.delete(f"refresh:{jti}")

        return await self._issue_tokens(user_id)

    async def logout(self, refresh_token: str) -> None:
        try:
            payload = decode_token(refresh_token)
        except ValueError:
            return

        jti: str | None = payload.get("jti")
        if jti:
            await self._redis.delete(f"refresh:{jti}")

    async def get_user_by_id(self, user_id: str) -> User | None:
        import uuid

        try:
            uid = uuid.UUID(user_id)
        except ValueError:
            return None
        return await self._repo.get_by_id(uid)

    async def _issue_tokens(self, user_id: str) -> TokenResponse:
        access_token = create_access_token(user_id)
        refresh_token, jti = create_refresh_token(user_id)
        await self._redis.setex(f"refresh:{jti}", _REFRESH_TTL, user_id)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )
