"""S3-compatible file storage. Uses boto3 + thread executor for async compatibility.

When S3_ACCESS_KEY_ID is not set, falls back to local /tmp storage so the
dev environment works without a real S3/MinIO instance.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_DEV_ROOT = Path("/app/dev-storage")  # shared via ./backend:/app bind-mount in Docker


def _s3_configured() -> bool:
    return bool(settings.S3_ACCESS_KEY_ID)


def _client() -> Any:
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL or None,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        region_name=settings.S3_REGION,
    )


async def upload_file(data: bytes, key: str) -> None:
    """Upload bytes to S3 (or local fallback) under the given key."""
    if not _s3_configured():
        path = _DEV_ROOT / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        logger.debug("local-storage upload", extra={"key": key})
        return

    def _do() -> None:
        _client().put_object(Bucket=settings.S3_BUCKET_NAME, Key=key, Body=data)

    await asyncio.get_running_loop().run_in_executor(None, _do)


async def download_file(key: str) -> bytes:
    """Download bytes from S3 (or local fallback) by key."""
    if not _s3_configured():
        path = _DEV_ROOT / key
        if not path.exists():
            raise FileNotFoundError(f"Local dev file not found: {key}")
        return path.read_bytes()

    def _do() -> bytes:
        resp = _client().get_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
        return resp["Body"].read()  # type: ignore[no-any-return]

    return await asyncio.get_running_loop().run_in_executor(None, _do)


async def delete_file(key: str) -> None:
    """Delete a file from S3 (or local fallback) by key."""
    if not _s3_configured():
        path = _DEV_ROOT / key
        if path.exists():
            path.unlink()
        return

    def _do() -> None:
        _client().delete_object(Bucket=settings.S3_BUCKET_NAME, Key=key)

    await asyncio.get_running_loop().run_in_executor(None, _do)
