"""Shared text embedding utility — retrieval, memory, and document ingest."""

from __future__ import annotations

import asyncio
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-small"
_EMBEDDING_DIM = 1536
_RETRY_DELAYS = [10, 30, 60, 120]  # seconds between retries on 429


async def embed_text(text: str) -> list[float]:
    """Generate embeddings via OpenAI text-embedding-3-small.

    Retries up to 4 times with increasing delays on rate-limit (429) errors.
    Raises RuntimeError immediately when OPENAI_API_KEY is not configured —
    a zero vector would produce undefined cosine similarity (NaN in pgvector).
    """
    if not settings.OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured; embedding is unavailable. "
            "Set the key or disable features that require it."
        )

    from openai import AsyncOpenAI, RateLimitError

    client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE or None,
    )

    last_exc: Exception | None = None
    for attempt, delay in enumerate([0, *_RETRY_DELAYS]):
        if delay:
            logger.warning("embed_text rate limited, retrying in %ds (attempt %d)", delay, attempt)
            await asyncio.sleep(delay)
        try:
            resp = await client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text,
                dimensions=_EMBEDDING_DIM,
            )
            return resp.data[0].embedding
        except RateLimitError as exc:
            last_exc = exc
        except Exception:
            raise

    raise RuntimeError("embed_text failed after retries") from last_exc
