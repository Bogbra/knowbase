from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.core.security import create_refresh_token, hash_password
from app.services.auth_service import AuthService
from tests.conftest import make_user


@pytest.fixture
def service(mock_user_repo: AsyncMock, mock_redis: AsyncMock) -> AuthService:
    return AuthService(mock_user_repo, mock_redis)


class TestRegister:
    async def test_register_returns_tokens(
        self, service: AuthService, mock_user_repo: AsyncMock
    ) -> None:
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.create.return_value = make_user(email="new@example.com")

        _, tokens = await service.register("new@example.com", "password123")

        assert tokens.access_token
        assert tokens.refresh_token
        assert tokens.token_type == "bearer"

    async def test_register_duplicate_email_raises(
        self, service: AuthService, mock_user_repo: AsyncMock
    ) -> None:
        mock_user_repo.get_by_email.return_value = make_user()

        with pytest.raises(EmailAlreadyExistsError):
            await service.register("existing@example.com", "password123")


class TestLogin:
    async def test_login_valid_credentials(
        self, service: AuthService, mock_user_repo: AsyncMock
    ) -> None:
        user = make_user()
        user.hashed_password = hash_password("secret123")
        mock_user_repo.get_by_email.return_value = user

        tokens = await service.login("test@example.com", "secret123")

        assert tokens.access_token
        assert tokens.refresh_token

    async def test_login_wrong_password_raises(
        self, service: AuthService, mock_user_repo: AsyncMock
    ) -> None:
        user = make_user()
        user.hashed_password = hash_password("correct-password")
        mock_user_repo.get_by_email.return_value = user

        with pytest.raises(InvalidCredentialsError):
            await service.login("test@example.com", "wrong-password")

    async def test_login_unknown_email_raises(
        self, service: AuthService, mock_user_repo: AsyncMock
    ) -> None:
        mock_user_repo.get_by_email.return_value = None

        with pytest.raises(InvalidCredentialsError):
            await service.login("nobody@example.com", "whatever")


class TestRefresh:
    async def test_refresh_valid_token_rotates(
        self, service: AuthService, mock_redis: AsyncMock
    ) -> None:
        user_id = "11111111-1111-1111-1111-111111111111"
        _, jti = create_refresh_token(user_id)
        token, _ = create_refresh_token(user_id)
        # Regenerate with the known jti embedded
        _, jti = create_refresh_token(user_id)
        token_str, jti = create_refresh_token(user_id)

        mock_redis.get.return_value = user_id.encode()

        new_tokens = await service.refresh(token_str)

        mock_redis.delete.assert_awaited_once()
        assert new_tokens.access_token
        assert new_tokens.refresh_token != token_str

    async def test_refresh_revoked_token_raises(
        self, service: AuthService, mock_redis: AsyncMock
    ) -> None:
        user_id = "22222222-2222-2222-2222-222222222222"
        token_str, _ = create_refresh_token(user_id)
        mock_redis.get.return_value = None  # Token revoked

        with pytest.raises(InvalidTokenError):
            await service.refresh(token_str)

    async def test_refresh_invalid_string_raises(self, service: AuthService) -> None:
        with pytest.raises(InvalidTokenError):
            await service.refresh("not.a.token")
