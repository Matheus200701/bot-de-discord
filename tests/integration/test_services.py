import os

import asyncpg
import pytest
from redis.asyncio import Redis

pytestmark = pytest.mark.integration


async def test_postgres_and_redis_are_reachable() -> None:
    database_url = os.environ["DATABASE_URL"]
    redis_url = os.environ["REDIS_URL"]

    connection = await asyncpg.connect(database_url.replace("postgresql+asyncpg://", "postgresql://", 1))
    try:
        assert await connection.fetchval("SELECT 1") == 1
    finally:
        await connection.close()

    redis = Redis.from_url(redis_url)
    try:
        assert await redis.ping() is True
    finally:
        await redis.aclose()
