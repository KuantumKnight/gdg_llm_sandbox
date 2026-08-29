from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import fakeredis.aioredis
import pytest

from app.domain.entities import SessionRecord
from app.repositories.redis import Keyspace
from app.repositories.state import RedisStateRepository, ReservationStatus


@pytest.fixture
async def redis_client() -> fakeredis.aioredis.FakeRedis:
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 8, 30, 8, 0, tzinfo=UTC)


@pytest.fixture
def session(now: datetime) -> SessionRecord:
    return SessionRecord(
        session_id="session-one",
        token_digest="bearer-digest",
        preset_id="stub-local",
        created_at=now,
        expires_at=now + timedelta(minutes=45),
        attempt_limit=3,
    )


@pytest.fixture
def repository(redis_client: fakeredis.aioredis.FakeRedis) -> RedisStateRepository:
    return RedisStateRepository(redis_client, keyspace=Keyspace("test"))


async def create_session(repository: RedisStateRepository, session: SessionRecord) -> None:
    await repository.create_session(session, cleanup_grace_seconds=300)


async def test_session_round_trip_and_ttl(
    repository: RedisStateRepository,
    redis_client: fakeredis.aioredis.FakeRedis,
    session: SessionRecord,
) -> None:
    await create_session(repository, session)

    loaded = await repository.get_session(session.session_id)

    assert loaded == session
    assert await redis_client.ttl(repository.keys.session(session.session_id)) > 0


async def test_reservation_completion_and_exact_replay(
    repository: RedisStateRepository, session: SessionRecord, now: datetime
) -> None:
    await create_session(repository, session)
    reserved = await repository.reserve_attempt(
        session=session,
        idempotency_digest="idem",
        request_digest="request",
        attempt_id="attempt-one",
        owner="owner-one",
        now=now,
        idempotency_ttl_seconds=600,
        lock_ttl_seconds=40,
        attempts_per_minute=6,
        preset_concurrency_limit=5,
    )

    assert reserved.status is ReservationStatus.RESERVED
    assert reserved.remaining_attempts == 2

    completed = await repository.complete_attempt(
        session=session,
        idempotency_digest="idem",
        owner="owner-one",
        encrypted_replay="ciphertext",
        solved_at=None,
        now=now + timedelta(seconds=1),
        idempotency_ttl_seconds=600,
    )
    replay = await repository.reserve_attempt(
        session=session,
        idempotency_digest="idem",
        request_digest="request",
        attempt_id="ignored",
        owner="owner-two",
        now=now + timedelta(seconds=2),
        idempotency_ttl_seconds=600,
        lock_ttl_seconds=40,
        attempts_per_minute=6,
        preset_concurrency_limit=5,
    )

    assert completed.remaining_attempts == 2
    assert replay.status is ReservationStatus.REPLAY
    assert replay.encrypted_replay == "ciphertext"
    loaded = await repository.get_session(session.session_id)
    assert loaded is not None
    assert loaded.charged_attempts == 1


async def test_concurrent_reservations_allow_only_one(
    repository: RedisStateRepository, session: SessionRecord, now: datetime
) -> None:
    await create_session(repository, session)

    async def reserve(index: int):
        return await repository.reserve_attempt(
            session=session,
            idempotency_digest=f"idem-{index}",
            request_digest=f"request-{index}",
            attempt_id=f"attempt-{index}",
            owner=f"owner-{index}",
            now=now,
            idempotency_ttl_seconds=600,
            lock_ttl_seconds=40,
            attempts_per_minute=20,
            preset_concurrency_limit=20,
        )

    results = await asyncio.gather(*(reserve(index) for index in range(10)))

    assert sum(result.status is ReservationStatus.RESERVED for result in results) == 1
    assert sum(result.status is ReservationStatus.IN_PROGRESS for result in results) == 9
    loaded = await repository.get_session(session.session_id)
    assert loaded is not None
    assert loaded.charged_attempts == 1


async def test_release_restores_attempt_and_allows_retry(
    repository: RedisStateRepository, session: SessionRecord, now: datetime
) -> None:
    await create_session(repository, session)
    await repository.reserve_attempt(
        session=session,
        idempotency_digest="idem",
        request_digest="request",
        attempt_id="attempt",
        owner="owner",
        now=now,
        idempotency_ttl_seconds=600,
        lock_ttl_seconds=40,
        attempts_per_minute=6,
        preset_concurrency_limit=5,
    )

    assert await repository.release_attempt(
        session=session, idempotency_digest="idem", owner="owner"
    )
    loaded = await repository.get_session(session.session_id)
    assert loaded is not None
    assert loaded.charged_attempts == 0


async def test_idempotency_conflict_and_unknown_outcome(
    repository: RedisStateRepository, session: SessionRecord, now: datetime
) -> None:
    await create_session(repository, session)
    await repository.reserve_attempt(
        session=session,
        idempotency_digest="idem",
        request_digest="first",
        attempt_id="attempt",
        owner="owner",
        now=now,
        idempotency_ttl_seconds=600,
        lock_ttl_seconds=40,
        attempts_per_minute=6,
        preset_concurrency_limit=5,
    )
    conflict = await repository.reserve_attempt(
        session=session,
        idempotency_digest="idem",
        request_digest="other",
        attempt_id="other",
        owner="other",
        now=now,
        idempotency_ttl_seconds=600,
        lock_ttl_seconds=40,
        attempts_per_minute=6,
        preset_concurrency_limit=5,
    )

    assert conflict.status is ReservationStatus.IDEMPOTENCY_CONFLICT
    assert await repository.mark_outcome_unknown(
        session=session,
        idempotency_digest="idem",
        owner="owner",
        now=now + timedelta(seconds=30),
        idempotency_ttl_seconds=600,
    )
    record = await repository.get_idempotency(
        session_id=session.session_id, idempotency_digest="idem"
    )
    assert record is not None
    assert record.state == "outcome_unknown"


async def test_attempt_limit_and_solved_state_block_new_calls(
    repository: RedisStateRepository, session: SessionRecord, now: datetime
) -> None:
    limited_session = SessionRecord(
        session_id=session.session_id,
        token_digest=session.token_digest,
        preset_id=session.preset_id,
        created_at=session.created_at,
        expires_at=session.expires_at,
        attempt_limit=1,
    )
    await create_session(repository, limited_session)
    await repository.reserve_attempt(
        session=limited_session,
        idempotency_digest="first",
        request_digest="first",
        attempt_id="first",
        owner="first",
        now=now,
        idempotency_ttl_seconds=600,
        lock_ttl_seconds=40,
        attempts_per_minute=6,
        preset_concurrency_limit=5,
    )
    await repository.complete_attempt(
        session=limited_session,
        idempotency_digest="first",
        owner="first",
        encrypted_replay="cipher",
        solved_at=None,
        now=now,
        idempotency_ttl_seconds=600,
    )
    exhausted = await repository.reserve_attempt(
        session=limited_session,
        idempotency_digest="second",
        request_digest="second",
        attempt_id="second",
        owner="second",
        now=now,
        idempotency_ttl_seconds=600,
        lock_ttl_seconds=40,
        attempts_per_minute=6,
        preset_concurrency_limit=5,
    )

    assert exhausted.status is ReservationStatus.ATTEMPTS_EXHAUSTED
    solved_at = await repository.mark_solved(session.session_id, now + timedelta(seconds=2))
    assert solved_at == now + timedelta(seconds=2)
    solved = await repository.reserve_attempt(
        session=limited_session,
        idempotency_digest="third",
        request_digest="third",
        attempt_id="third",
        owner="third",
        now=now + timedelta(seconds=3),
        idempotency_ttl_seconds=600,
        lock_ttl_seconds=40,
        attempts_per_minute=6,
        preset_concurrency_limit=5,
    )
    assert solved.status is ReservationStatus.SESSION_SOLVED


async def test_token_bucket_limits_and_refills(
    repository: RedisStateRepository, now: datetime
) -> None:
    first = await repository.consume_rate_limit(
        scope="ip", identifier="opaque", capacity=2, window_seconds=60, now=now
    )
    second = await repository.consume_rate_limit(
        scope="ip", identifier="opaque", capacity=2, window_seconds=60, now=now
    )
    limited = await repository.consume_rate_limit(
        scope="ip", identifier="opaque", capacity=2, window_seconds=60, now=now
    )
    refilled = await repository.consume_rate_limit(
        scope="ip",
        identifier="opaque",
        capacity=2,
        window_seconds=60,
        now=now + timedelta(seconds=31),
    )

    assert first == (True, 0)
    assert second == (True, 0)
    assert limited[0] is False
    assert limited[1] > 0
    assert refilled == (True, 0)


async def test_raw_redis_contains_no_proof_or_provider_key(
    repository: RedisStateRepository,
    redis_client: fakeredis.aioredis.FakeRedis,
    session: SessionRecord,
) -> None:
    await create_session(repository, session)

    raw = await redis_client.hgetall(repository.keys.session(session.session_id))
    serialized = repr(raw)

    assert "GDG{" not in serialized
    assert "provider-key" not in serialized
