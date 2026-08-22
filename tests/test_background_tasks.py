import pytest
from fastapi.testclient import TestClient

from app.background.redis_coordinator import (
    RedisCoordinator,
    TaskAlreadyRunning,
)


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str | int] = {}

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True

    def get(self, key):
        return self.values.get(key)

    def setex(self, key, seconds, value):
        self.values[key] = value

    def incr(self, key):
        self.values[key] = int(self.values.get(key, 0)) + 1
        return self.values[key]

    def expire(self, key, seconds):
        return True

    def eval(self, script, count, key, token):
        if self.values.get(key) == token:
            del self.values[key]
            return 1
        return 0


def test_redis_lock_prevents_duplicate_and_is_released() -> None:
    redis = FakeRedis()
    first = RedisCoordinator(redis)
    second = RedisCoordinator(redis)

    with first.lock("gmail:42"):
        with pytest.raises(TaskAlreadyRunning):
            with second.lock("gmail:42"):
                pass

    with second.lock("gmail:42"):
        assert redis.get("applymatch:lock:gmail:42") is not None


def test_redis_rate_limit_and_cache() -> None:
    coordinator = RedisCoordinator(FakeRedis())
    coordinator.cache_set("france-travail", "cached", seconds=60)
    assert coordinator.cache_get("france-travail") == "cached"
    assert coordinator.allow_request("france-travail", limit=2, window_seconds=60)
    assert coordinator.allow_request("france-travail", limit=2, window_seconds=60)
    assert not coordinator.allow_request(
        "france-travail", limit=2, window_seconds=60
    )


def test_background_tasks_are_disabled_by_default(
    authenticated_client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.delenv("BACKGROUND_TASKS_ENABLED", raising=False)
    response = authenticated_client.post("/background-tasks/collect-offers")
    assert response.status_code == 503


def test_gmail_task_uses_stable_idempotency_id(
    authenticated_client: TestClient,
    monkeypatch,
) -> None:
    calls: list[dict] = []
    monkeypatch.setenv("BACKGROUND_TASKS_ENABLED", "true")
    monkeypatch.setattr(
        "app.api.routes.background_tasks.send_gmail.apply_async",
        lambda **kwargs: calls.append(kwargs),
    )

    first = authenticated_client.post("/background-tasks/gmail/42/send")
    second = authenticated_client.post("/background-tasks/gmail/42/send")

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["task_id"] == "gmail-delivery-42"
    assert second.json()["task_id"] == "gmail-delivery-42"
    assert calls == [
        {"args": [42, False], "task_id": "gmail-delivery-42"},
        {"args": [42, False], "task_id": "gmail-delivery-42"},
    ]
