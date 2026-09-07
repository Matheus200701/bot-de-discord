from __future__ import annotations

import time

from redis.asyncio import Redis


class RateLimitExceeded(Exception):
    pass


class RedisRateLimiter:
    """Fixed-window distributed limiter with an atomic Redis Lua operation."""

    SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return current
"""

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
        count = int(await self.redis.eval(self.SCRIPT, 1, redis_key, self.window_seconds + 1))
        if count > self.limit:
            raise RateLimitExceeded(key)
        return self.limit - count
