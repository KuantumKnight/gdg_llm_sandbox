"""Redis-backed session, quota, idempotency, and solve state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

from redis.exceptions import RedisError

from app.domain.entities import SessionRecord
from app.domain.errors import StateUnavailableError
from app.repositories.redis import Keyspace, RedisLike

_LUA_DIR = Path(__file__).resolve().parent / "lua"


class ReservationStatus(StrEnum):
    RESERVED = "reserved"
    REPLAY = "replay"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    IN_PROGRESS = "in_progress"
    SESSION_NOT_FOUND = "session_not_found"
    SESSION_EXPIRED = "session_expired"
    SESSION_SOLVED = "session_solved"
    ATTEMPTS_EXHAUSTED = "attempts_exhausted"
    RATE_LIMITED = "rate_limited"
    PRESET_BUSY = "preset_busy"


@dataclass(frozen=True, slots=True)
class ReservationResult:
    status: ReservationStatus
    attempt_id: str | None = None
    remaining_attempts: int | None = None
    encrypted_replay: str | None = None
    detail: str | None = None
    retry_after_ms: int | None = None


@dataclass(frozen=True, slots=True)
class CompletionState:
    solved_at: datetime | None
    remaining_attempts: int


@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    state: str
    request_digest: str
    attempt_id: str
    encrypted_replay: str | None
    owner: str


def _load_lua(name: str) -> str:
    return (_LUA_DIR / name).read_text(encoding="utf-8")


class RedisStateRepository:
    def __init__(self, client: RedisLike, *, keyspace: Keyspace) -> None:
        self.client = client
        self.keys = keyspace
        self._reserve_script = _load_lua("reserve_attempt.lua")
        self._complete_script = _load_lua("complete_attempt.lua")
        self._release_script = _load_lua("release_attempt.lua")
        self._unknown_script = _load_lua("mark_unknown.lua")
        self._solved_script = _load_lua("mark_solved.lua")
        self._bucket_script = _load_lua("token_bucket.lua")

    async def ping(self) -> bool:
        try:
            return bool(await self.client.ping())
        except RedisError as exc:
            raise StateUnavailableError("shared state unavailable") from exc

    async def close(self) -> None:
        await self.client.aclose()

    async def create_session(self, record: SessionRecord, *, cleanup_grace_seconds: int) -> None:
        key = self.keys.session(record.session_id)
        ttl = max(
            1,
            int((record.expires_at - record.created_at).total_seconds()) + cleanup_grace_seconds,
        )
        mapping = {
            "session_id": record.session_id,
            "token_digest": record.token_digest,
            "preset_id": record.preset_id,
            "created_at_ms": str(_to_ms(record.created_at)),
            "expires_at_ms": str(_to_ms(record.expires_at)),
            "attempt_limit": str(record.attempt_limit),
            "charged_attempts": str(record.charged_attempts),
            "solved_at_ms": "" if record.solved_at is None else str(_to_ms(record.solved_at)),
            "prompt_version": record.prompt_version,
        }
        try:
            async with self.client.pipeline(transaction=True) as pipe:
                pipe.hset(key, mapping=mapping)
                pipe.expire(key, ttl)
                await pipe.execute()
        except RedisError as exc:
            raise StateUnavailableError("could not create session") from exc

    async def get_session(self, session_id: str) -> SessionRecord | None:
        try:
            raw = cast(dict[str, str], await self.client.hgetall(self.keys.session(session_id)))
        except RedisError as exc:
            raise StateUnavailableError("could not read session") from exc
        if not raw:
            return None
        solved_raw = raw.get("solved_at_ms", "")
        return SessionRecord(
            session_id=raw["session_id"],
            token_digest=raw["token_digest"],
            preset_id=raw["preset_id"],
            created_at=_from_ms(raw["created_at_ms"]),
            expires_at=_from_ms(raw["expires_at_ms"]),
            attempt_limit=int(raw["attempt_limit"]),
            charged_attempts=int(raw.get("charged_attempts", "0")),
            solved_at=_from_ms(solved_raw) if solved_raw else None,
            prompt_version=raw.get("prompt_version", "gatekeeper-v1"),
        )

    async def consume_rate_limit(
        self, *, scope: str, identifier: str, capacity: int, window_seconds: int, now: datetime
    ) -> tuple[bool, int]:
        result = await self._eval(
            self._bucket_script,
            [self.keys.generic_rate(scope, identifier)],
            [_to_ms(now), capacity, window_seconds * 1000],
        )
        return result[0] == "allowed", int(result[1])

    async def reserve_attempt(
        self,
        *,
        session: SessionRecord,
        idempotency_digest: str,
        request_digest: str,
        attempt_id: str,
        owner: str,
        now: datetime,
        idempotency_ttl_seconds: int,
        lock_ttl_seconds: int,
        attempts_per_minute: int,
        preset_concurrency_limit: int,
    ) -> ReservationResult:
        result = await self._eval(
            self._reserve_script,
            [
                self.keys.session(session.session_id),
                self.keys.idempotency(session.session_id, idempotency_digest),
                self.keys.attempt_lock(session.session_id),
                self.keys.session_rate(session.session_id),
                self.keys.preset_concurrency(session.preset_id),
            ],
            [
                _to_ms(now),
                request_digest,
                attempt_id,
                owner,
                session.attempt_limit,
                idempotency_ttl_seconds * 1000,
                lock_ttl_seconds * 1000,
                attempts_per_minute,
                preset_concurrency_limit,
            ],
        )
        status = ReservationStatus(result[0])
        if status is ReservationStatus.RESERVED:
            return ReservationResult(
                status, attempt_id=result[1], remaining_attempts=int(result[2])
            )
        if status is ReservationStatus.REPLAY:
            return ReservationResult(status, encrypted_replay=result[1])
        if status is ReservationStatus.RATE_LIMITED:
            return ReservationResult(status, retry_after_ms=int(result[1]))
        return ReservationResult(status, detail=result[1] if len(result) > 1 else None)

    async def complete_attempt(
        self,
        *,
        session: SessionRecord,
        idempotency_digest: str,
        owner: str,
        encrypted_replay: str,
        solved_at: datetime | None,
        now: datetime,
        idempotency_ttl_seconds: int,
    ) -> CompletionState:
        result = await self._eval(
            self._complete_script,
            [
                self.keys.session(session.session_id),
                self.keys.idempotency(session.session_id, idempotency_digest),
                self.keys.attempt_lock(session.session_id),
                self.keys.preset_concurrency(session.preset_id),
            ],
            [
                owner,
                encrypted_replay,
                "" if solved_at is None else _to_ms(solved_at),
                _to_ms(now),
                idempotency_ttl_seconds * 1000,
            ],
        )
        if result[0] != "completed":
            raise StateUnavailableError("attempt reservation disappeared before completion")
        return CompletionState(
            solved_at=_from_ms(result[1]) if result[1] else None,
            remaining_attempts=int(result[2]),
        )

    async def release_attempt(
        self,
        *,
        session: SessionRecord,
        idempotency_digest: str,
        owner: str,
    ) -> bool:
        result = await self._eval(
            self._release_script,
            [
                self.keys.session(session.session_id),
                self.keys.idempotency(session.session_id, idempotency_digest),
                self.keys.attempt_lock(session.session_id),
                self.keys.preset_concurrency(session.preset_id),
            ],
            [owner],
        )
        return result[0] == "released"

    async def mark_outcome_unknown(
        self,
        *,
        session: SessionRecord,
        idempotency_digest: str,
        owner: str,
        now: datetime,
        idempotency_ttl_seconds: int,
    ) -> bool:
        result = await self._eval(
            self._unknown_script,
            [
                self.keys.idempotency(session.session_id, idempotency_digest),
                self.keys.attempt_lock(session.session_id),
                self.keys.preset_concurrency(session.preset_id),
            ],
            [owner, _to_ms(now), idempotency_ttl_seconds * 1000],
        )
        return result[0] == "outcome_unknown"

    async def mark_solved(self, session_id: str, solved_at: datetime) -> datetime:
        result = await self._eval(
            self._solved_script,
            [self.keys.session(session_id)],
            [_to_ms(solved_at)],
        )
        if result[0] != "solved":
            raise StateUnavailableError("session disappeared before solve")
        return _from_ms(result[1])

    async def get_idempotency(
        self, *, session_id: str, idempotency_digest: str
    ) -> IdempotencyRecord | None:
        try:
            raw = cast(
                dict[str, str],
                await self.client.hgetall(self.keys.idempotency(session_id, idempotency_digest)),
            )
        except RedisError as exc:
            raise StateUnavailableError("could not read idempotency state") from exc
        if not raw:
            return None
        return IdempotencyRecord(
            state=raw["state"],
            request_digest=raw["request_digest"],
            attempt_id=raw["attempt_id"],
            encrypted_replay=raw.get("encrypted_replay"),
            owner=raw["owner"],
        )

    async def _eval(self, script: str, keys: list[str], args: list[Any]) -> list[str]:
        try:
            raw = await self.client.eval(script, len(keys), *keys, *args)
            return [str(item) for item in cast(list[Any], raw)]
        except RedisError as exc:
            raise StateUnavailableError("shared-state transition failed") from exc


def _to_ms(value: datetime) -> int:
    if value.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return int(value.timestamp() * 1000)


def _from_ms(value: str | int) -> datetime:
    return datetime.fromtimestamp(int(value) / 1000, tz=UTC)
