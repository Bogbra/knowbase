import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.db.models.memory import MemoryScope
from app.services.memory_service import MemoryService


@pytest.fixture
def service() -> MemoryService:
    return MemoryService(AsyncMock())


class TestCreate:
    async def test_embeds_content_before_persisting(self, service: MemoryService) -> None:
        fake_embedding = [0.1, 0.2, 0.3]
        service._repo.create = AsyncMock()  # type: ignore[method-assign]

        with patch(
            "app.services.memory_service.embed_text",
            AsyncMock(return_value=fake_embedding),
        ) as mock_embed:
            await service.create(
                user_id=uuid.uuid4(),
                scope=MemoryScope.workspace,
                content="The user prefers dark mode.",
            )

        mock_embed.assert_awaited_once_with("The user prefers dark mode.")
        _, kwargs = service._repo.create.call_args
        assert kwargs["embedding"] == fake_embedding

    async def test_propagates_embedding_failure(self, service: MemoryService) -> None:
        service._repo.create = AsyncMock()  # type: ignore[method-assign]

        with (
            patch(
                "app.services.memory_service.embed_text",
                AsyncMock(side_effect=RuntimeError("OPENAI_API_KEY is not configured")),
            ),
            pytest.raises(RuntimeError),
        ):
            await service.create(
                user_id=uuid.uuid4(),
                scope=MemoryScope.workspace,
                content="fact",
            )

        service._repo.create.assert_not_awaited()
