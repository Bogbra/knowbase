import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.tools.memory_tools import write_memory
from app.db.models.memory import MemoryScope


def _mock_memory() -> MagicMock:
    mem = MagicMock()
    mem.id = uuid.uuid4()
    mem.content = "fact"
    mem.scope = MemoryScope.workspace
    mem.tags = []
    mem.metadata_ = {}
    return mem


class TestWriteMemory:
    async def test_embeds_content_before_persisting(self) -> None:
        fake_embedding = [0.1, 0.2, 0.3]
        with (
            patch(
                "app.agents.tools.memory_tools.embed_text",
                AsyncMock(return_value=fake_embedding),
            ) as mock_embed,
            patch("app.agents.tools.memory_tools.MemoryRepository") as mock_repo_cls,
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.create = AsyncMock(return_value=_mock_memory())

            await write_memory(
                user_id=str(uuid.uuid4()),
                content="The user prefers dark mode.",
                scope=MemoryScope.workspace,
                session=AsyncMock(),
            )

            mock_embed.assert_awaited_once_with("The user prefers dark mode.")
            _, kwargs = mock_repo.create.call_args
            assert kwargs["embedding"] == fake_embedding
