"""Fixtures for integration tests — real PostgreSQL session, eval corpus ingestion."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio

import app.db.models  # noqa: F401 — registers all models with SQLAlchemy Base


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[object, None]:
    """Function-scoped async session backed by the test DATABASE_URL."""
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="session")
async def corpus_workspace_id() -> AsyncGenerator[str, None]:
    """Ingest the eval corpus once per test session; yield workspace UUID as str.

    Skips when OPENAI_API_KEY is not set so the integration test session
    degrades gracefully in CI without an API key.

    Declared as a session-scoped async fixture so it shares the same event
    loop as the test functions (asyncio_default_fixture_loop_scope = "session"
    in pyproject.toml). This avoids asyncpg cross-loop InterfaceErrors that
    occur when the old sync + asyncio.new_event_loop() approach left pool
    connections bound to a different loop.
    """
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set — skipping corpus ingestion")

    from app.db.session import AsyncSessionLocal
    from eval.fixtures import create_eval_workspace, ingest_corpus

    async with AsyncSessionLocal() as session:
        _, workspace = await create_eval_workspace(session)
        await ingest_corpus(session, workspace.id, embed=True)
        await session.commit()

    yield str(workspace.id)
