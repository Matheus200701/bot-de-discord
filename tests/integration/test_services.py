import os

import pytest

pytestmark = pytest.mark.integration


async def test_postgres_and_redis_are_configured() -> None:
    database_url = os.environ.get("DATABASE_URL", "")
    redis_url = os.environ.get("REDIS_URL", "")
    assert database_url.startswith("postgresql+asyncpg://")
    assert redis_url.startswith("redis://")
