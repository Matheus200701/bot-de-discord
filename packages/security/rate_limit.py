from __future__ import annotations

import time

from redis.asyncio import Redis


class RateLimitExceeded(Exception):
    pass


class RedisRateLimiter:
    """Fixed-window distributed limiter; fail closed for protected mutations."""

    def __init__(self, redis: Redis, limit: int, window_seconds: int) -> None:
        if limit <= 0 or window_seconds <= 0:
            raise ValueError("limit_and_window_must_be_positive")
        self.redis = redis
        self.limit = limit
        self.window_seconds = window_seconds

    async def check(self, key: str) -> int:
        now = int(time.time())
        bucket = now // self.window_seconds
        redis_key = f"commerce:ratelimit:{key}:{bucket}"
        count = await self.redis.incr(redis_key)
        if count == 1:
            await self.redis.expire(redis_key, self.window_seconds + 1)
        if count > self.limit:
            raise RateLimitExceeded(key)
        return self.limit - count
