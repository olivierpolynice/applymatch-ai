import os
import secrets
from contextlib import contextmanager
from typing import Iterator


class TaskAlreadyRunning(RuntimeError):
    pass


class RedisCoordinator:
    def __init__(self, client=None) -> None:
        if client is None:
            from redis import Redis

            client = Redis.from_url(
                os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                decode_responses=True,
            )
        self.client = client

    @contextmanager
    def lock(self, key: str, *, expires: int = 900) -> Iterator[None]:
        token = secrets.token_urlsafe(24)
        acquired = self.client.set(
            f"applymatch:lock:{key}", token, nx=True, ex=expires
        )
        if not acquired:
            raise TaskAlreadyRunning(f"Task already running: {key}")
        try:
            yield
        finally:
            self.client.eval(
                "if redis.call('get', KEYS[1]) == ARGV[1] then "
                "return redis.call('del', KEYS[1]) else return 0 end",
                1,
                f"applymatch:lock:{key}",
                token,
            )

    def cache_get(self, key: str) -> str | None:
        return self.client.get(f"applymatch:cache:{key}")

    def cache_set(self, key: str, value: str, *, seconds: int = 300) -> None:
        self.client.setex(f"applymatch:cache:{key}", seconds, value)

    def allow_request(
        self, key: str, *, limit: int, window_seconds: int
    ) -> bool:
        redis_key = f"applymatch:rate:{key}"
        count = self.client.incr(redis_key)
        if count == 1:
            self.client.expire(redis_key, window_seconds)
        return count <= limit
