import pytest

from packages.security.rate_limit import RateLimitExceeded, RedisRateLimiter


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    async def expire(self, key: str, seconds: int) -> bool:
        return True


@pytest.mark.asyncio
async def test_rate_limiter_blocks_after_limit() -> None:
    limiter = RedisRateLimiter(FakeRedis(), limit=2, window_seconds=60)  # type: ignore[arg-type]
    assert await limiter.check("tenant:user") == 1
    assert await limiter.check("tenant:user") == 0
    with pytest.raises(RateLimitExceeded):
        await limiter.check("tenant:user")
