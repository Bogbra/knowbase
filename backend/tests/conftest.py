import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models.user import User, UserRole


def make_user(
    user_id: str | None = None,
    email: str = "test@example.com",
    role: UserRole = UserRole.user,
    is_active: bool = True,
) -> User:
    user = MagicMock(spec=User)
    user.id = uuid.UUID(user_id) if user_id else uuid.uuid4()
    user.email = email
    user.hashed_password = "$argon2id$v=19$m=65536,t=3,p=4$fake"
    user.role = role
    user.is_active = is_active
    user.created_at = datetime.now(UTC)
    return user


@pytest.fixture
def mock_user_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_redis() -> AsyncMock:
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    return redis
