"""Unit tests for API key hashing and repository logic."""

import hashlib
import uuid
from unittest.mock import AsyncMock, MagicMock

from app.api.v1.api_keys import _hash_key, _make_raw_key
from app.db.repositories.api_key_repository import ApiKeyRepository


class TestKeyFormat:
    def test_raw_key_has_kb_prefix(self) -> None:
        key = _make_raw_key()
        assert key.startswith("kb_")

    def test_raw_key_length(self) -> None:
        key = _make_raw_key()
        # "kb_" + 64 hex chars (32 bytes)
        assert len(key) == 3 + 64

    def test_two_keys_are_different(self) -> None:
        assert _make_raw_key() != _make_raw_key()

    def test_hash_is_sha256_hex(self) -> None:
        raw = "kb_" + "a" * 64
        result = _hash_key(raw)
        expected = hashlib.sha256(raw.encode()).hexdigest()
        assert result == expected
        assert len(result) == 64

    def test_same_key_same_hash(self) -> None:
        raw = _make_raw_key()
        assert _hash_key(raw) == _hash_key(raw)

    def test_different_keys_different_hashes(self) -> None:
        a, b = _make_raw_key(), _make_raw_key()
        assert _hash_key(a) != _hash_key(b)


class TestApiKeyRepository:
    def _make_repo(self) -> tuple[ApiKeyRepository, AsyncMock]:
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        repo = ApiKeyRepository(session)
        return repo, session

    async def test_get_by_hash_returns_none_when_not_found(self) -> None:
        repo, session = self._make_repo()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        result = await repo.get_by_hash("nonexistent_hash")
        assert result is None

    async def test_revoke_returns_false_when_no_rows_updated(self) -> None:
        repo, session = self._make_repo()
        mock_result = MagicMock()
        mock_result.rowcount = 0
        session.execute.return_value = mock_result

        result = await repo.revoke(uuid.uuid4(), uuid.uuid4())
        assert result is False

    async def test_revoke_returns_true_when_row_updated(self) -> None:
        repo, session = self._make_repo()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        session.execute.return_value = mock_result

        result = await repo.revoke(uuid.uuid4(), uuid.uuid4())
        assert result is True
