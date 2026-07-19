import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

logger = logging.getLogger(__name__)


async def startup(ctx: dict[str, object]) -> None:
    structlog.get_logger().info("worker_started")


async def shutdown(ctx: dict[str, object]) -> None:
    structlog.get_logger().info("worker_stopped")


class WorkerSettings:
    functions: list[object] = []  # tasks registered here in later phases
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(os.getenv("REDIS_URL") or "redis://localhost:6379/0")
    max_jobs = 10
    job_timeout = 300  # 5 minutes


@asynccontextmanager
async def get_redis_pool(dsn: str = "redis://localhost:6379/0") -> AsyncIterator[ArqRedis]:
    pool = await create_pool(RedisSettings.from_dsn(dsn))
    try:
        yield pool
    finally:
        await pool.aclose()
