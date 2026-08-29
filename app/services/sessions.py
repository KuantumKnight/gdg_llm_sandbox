"""Round admission and session authorization service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.core.config import ProviderPreset, Settings
from app.core.security import (
    SessionCredentials,
    constant_time_secret_matches,
    new_session_credentials,
    opaque_identifier,
    token_digest,
    verify_token,
)
from app.domain.entities import SessionRecord
from app.domain.errors import (
    PresetNotAvailableError,
    RateLimitedError,
    RoundAccessDeniedError,
    SessionExpiredError,
    SessionNotFoundError,
)
from app.repositories.state import RedisStateRepository


@dataclass(frozen=True, slots=True)
class CreatedSession:
    record: SessionRecord
    credentials: SessionCredentials
    preset: ProviderPreset


class SessionService:
    def __init__(self, *, settings: Settings, repository: RedisStateRepository) -> None:
        self.settings = settings
        self.repository = repository

    async def create_session(
        self, *, round_code: str, preset_id: str, client_ip: str, now: datetime
    ) -> CreatedSession:
        ip_ref = opaque_identifier(
            client_ip, self.settings.idempotency_digest_secret.get_secret_value()
        )
        allowed, _retry_ms = await self.repository.consume_rate_limit(
            scope="session-create-ip",
            identifier=ip_ref,
            capacity=self.settings.ip_session_creations_per_window,
            window_seconds=self.settings.ip_session_window_seconds,
            now=now,
        )
        if not allowed:
            raise RateLimitedError()
        if not constant_time_secret_matches(
            round_code, self.settings.round_access_code.get_secret_value()
        ):
            raise RoundAccessDeniedError()
        preset = self.settings.preset_by_id(preset_id)
        if preset is None:
            raise PresetNotAvailableError()

        credentials = new_session_credentials()
        record = SessionRecord(
            session_id=credentials.session_id,
            token_digest=token_digest(
                credentials.bearer_token,
                self.settings.session_token_pepper.get_secret_value(),
            ),
            preset_id=preset.id,
            created_at=now,
            expires_at=now + timedelta(seconds=self.settings.session_ttl_seconds),
            attempt_limit=self.settings.attempt_limit,
        )
        await self.repository.create_session(
            record, cleanup_grace_seconds=self.settings.session_cleanup_grace_seconds
        )
        return CreatedSession(record=record, credentials=credentials, preset=preset)

    async def authenticate(
        self, *, session_id: str, bearer_token: str, now: datetime
    ) -> tuple[SessionRecord, ProviderPreset]:
        record = await self.repository.get_session(session_id)
        if record is None or not bearer_token:
            raise SessionNotFoundError()
        if not verify_token(
            bearer_token,
            record.token_digest,
            self.settings.session_token_pepper.get_secret_value(),
        ):
            raise SessionNotFoundError()
        if now >= record.expires_at:
            raise SessionExpiredError()
        preset = self.settings.preset_by_id(record.preset_id)
        if preset is None:
            raise PresetNotAvailableError()
        return record, preset
