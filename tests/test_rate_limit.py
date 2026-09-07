import pytest
from fakeredis.aioredis import FakeRedis

from packages.security.rate_limit import RateLimitExceeded, RedisRateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_blocks_after_limit() -> None:
    redis = FakeRedis()
    limiter = RedisRateLimiter(redis, limit=2, window_seconds=60)

    assert await limiter.check("tenant:user") == 1
    assert await limiter.check("tenant:user") == 0
    with pytest.raises(RateLimitExceeded):
        await limiter.check("tenant:user")

    await redis.aclose()
