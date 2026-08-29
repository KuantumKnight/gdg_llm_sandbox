from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from redis.asyncio import Redis

from app.domain.entities import SessionRecord
from app.repositories.redis import Keyspace
from app.repositories.state import RedisStateRepository, ReservationStatus

pytestmark = pytest.mark.real_redis


@pytest.fixture
async def real_repository() -> AsyncIterator[RedisStateRepository]:
    url = os.environ.get("TEST_REDIS_URL")
    if not url:
        pytest.skip("TEST_REDIS_URL is not configured")
    namespace = f"gdg-real-test:{uuid.uuid4().hex}"
    client = Redis.from_url(url, decode_responses=True)
    repository = RedisStateRepository(client, keyspace=Keyspace(namespace))
    try:
        assert await repository.ping()
        yield repository
    finally:
        keys = [key async for key in client.scan_iter(match=f"{namespace}:*")]
        if keys:
            await client.delete(*keys)
        await client.aclose()


async def test_real_redis_executes_atomic_session_and_replay_flow(
    real_repository: RedisStateRepository,
) -> None:
    now = datetime.now(UTC)
    session = SessionRecord(
        session_id="real-redis-session",
        token_digest="opaque-token-digest",
        preset_id="stub-local",
        created_at=now,
        expires_at=now + timedelta(minutes=5),
        attempt_limit=2,
    )
    await real_repository.create_session(session, cleanup_grace_seconds=30)
    reserved = await real_repository.reserve_attempt(
        session=session,
        idempotency_digest="idem",
        request_digest="request",
        attempt_id="attempt",
        owner="owner",
        now=now,
        idempotency_ttl_seconds=60,
        lock_ttl_seconds=10,
        attempts_per_minute=6,
        preset_concurrency_limit=2,
    )
    await real_repository.complete_attempt(
        session=session,
        idempotency_digest="idem",
        owner="owner",
        encrypted_replay="ciphertext",
        solved_at=None,
        now=now + timedelta(seconds=1),
        idempotency_ttl_seconds=60,
    )
    replay = await real_repository.reserve_attempt(
        session=session,
        idempotency_digest="idem",
        request_digest="request",
        attempt_id="ignored",
        owner="other",
        now=now + timedelta(seconds=2),
        idempotency_ttl_seconds=60,
        lock_ttl_seconds=10,
        attempts_per_minute=6,
        preset_concurrency_limit=2,
    )

    assert reserved.status is ReservationStatus.RESERVED
    assert replay.status is ReservationStatus.REPLAY
    assert replay.encrypted_replay == "ciphertext"
