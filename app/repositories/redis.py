"""Redis connection lifecycle and versioned key names."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis


def create_redis_client(url: str) -> Redis:
    return Redis.from_url(
        url,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
        health_check_interval=30,
    )


@dataclass(frozen=True, slots=True)
class Keyspace:
    environment: str
    prefix: str = "sandbox:v1"

    @property
    def root(self) -> str:
        return f"{self.prefix}:{self.environment}"

    def session(self, session_id: str) -> str:
        return f"{self.root}:session:{session_id}"

    def idempotency(self, session_id: str, key_digest: str) -> str:
        return f"{self.root}:idem:{session_id}:{key_digest}"

    def attempt_lock(self, session_id: str) -> str:
        return f"{self.root}:lock:attempt:{session_id}"

    def session_rate(self, session_id: str) -> str:
        return f"{self.root}:rate:session:{session_id}"

    def generic_rate(self, scope: str, identifier: str) -> str:
        return f"{self.root}:rate:{scope}:{identifier}"

    def preset_concurrency(self, preset_id: str) -> str:
        return f"{self.root}:concurrency:preset:{preset_id}"


RedisLike = Any
