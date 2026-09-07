import os

import pytest
from redis.asyncio import Redis

from packages.security.rate_limit import RateLimitExceeded, RedisRateLimiter

pytestmark = pytest.mark.integration


async def test_distributed_rate_limiter_enforces_window() -> None:
    redis = Redis.from_url(os.environ["REDIS_URL"])
    limiter = RedisRateLimiter(redis, limit=2, window_seconds=60)
    key = "phase15:rate-limit"
    try:
        await redis.delete(key)
        assert await limiter.check(key) == 1
        assert await limiter.check(key) == 0
        with pytest.raises(RateLimitExceeded):
            await limiter.check(key)
    finally:
        await redis.delete(key)
        await redis.aclose()
