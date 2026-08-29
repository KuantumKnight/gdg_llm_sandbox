"""End-to-end attempt orchestration with atomic charging and replay."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import SecretStr

from app.core.config import Settings
from app.core.security import canonical_request_digest, idempotency_key_digest
from app.domain.errors import (
    AttemptInProgressError,
    AttemptsExhaustedError,
    IdempotencyConflictError,
    PresetBusyError,
    PromptTooLargeError,
    RateLimitedError,
    SessionExpiredError,
    SessionNotFoundError,
    SessionSolvedError,
)
from app.observability.metrics import Metrics
from app.providers.base import ProviderRequest
from app.providers.errors import ProviderError
from app.providers.registry import ProviderRegistry
from app.repositories.state import RedisStateRepository, ReservationStatus
from app.schemas.attempts import AttemptData, UsageData
from app.services.challenge import (
    derive_proof_token,
    model_output_solves,
    render_challenge_messages,
)
from app.services.replay_crypto import ReplayCrypto
from app.services.sessions import SessionService


class AttemptService:
    def __init__(
        self,
        *,
        settings: Settings,
        repository: RedisStateRepository,
        provider_registry: ProviderRegistry,
        metrics: Metrics,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.provider_registry = provider_registry
        self.metrics = metrics
        self.sessions = SessionService(settings=settings, repository=repository)
        self.replay_crypto = ReplayCrypto(settings.replay_encryption_key.get_secret_value())

    async def submit(
        self,
        *,
        session_id: str,
        bearer_token: str,
        idempotency_key: str,
        prompt: str,
        participant_api_key: SecretStr | None,
        request_id: str,
    ) -> AttemptData:
        now = datetime.now(UTC)
        session, _preset = await self.sessions.authenticate(
            session_id=session_id, bearer_token=bearer_token, now=now
        )
        if session.solved_at is not None:
            raise SessionSolvedError()
        if len(prompt) > self.settings.prompt_max_characters:
            raise PromptTooLargeError()

        secret = self.settings.idempotency_digest_secret.get_secret_value()
        idem_digest = idempotency_key_digest(idempotency_key, secret)
        request_digest = canonical_request_digest(
            method="POST",
            path=f"/api/v1/sessions/{session_id}/attempts",
            body={"prompt": prompt},
            secret=secret,
        )
        attempt_id = str(uuid.uuid4())
        reservation = await self.repository.reserve_attempt(
            session=session,
            idempotency_digest=idem_digest,
            request_digest=request_digest,
            attempt_id=attempt_id,
            owner=request_id,
            now=now,
            idempotency_ttl_seconds=self.settings.idempotency_ttl_seconds,
            lock_ttl_seconds=int(self.settings.provider_timeout_seconds) + 10,
            attempts_per_minute=self.settings.session_attempts_per_minute,
            preset_concurrency_limit=self.settings.preset_concurrency_limit,
        )
        if reservation.status is ReservationStatus.REPLAY:
            self.metrics.idempotency_replays.inc()
            replay = self.replay_crypto.decrypt(
                reservation.encrypted_replay or "", associated_data=f"{session_id}:{idem_digest}"
            )
            return AttemptData.model_validate(replay["data"])
        self._raise_for_reservation(reservation.status)

        proof = derive_proof_token(
            session_id=session.session_id,
            created_at=session.created_at,
            secret=self.settings.proof_derivation_secret.get_secret_value(),
        )
        messages = render_challenge_messages(proof_token=proof, user_prompt=prompt)
        inflight_started = False
        try:
            _configured_preset, provider = self.provider_registry.get(session.preset_id)
            self.metrics.inflight_provider.labels(preset=session.preset_id).inc()
            inflight_started = True
            completion = await provider.complete(
                ProviderRequest(
                    system_prompt=messages.system,
                    user_prompt=messages.user,
                    max_output_tokens=self.settings.model_max_output_tokens,
                ),
                participant_api_key=participant_api_key,
            )
        except ProviderError as exc:
            self.metrics.record_attempt(
                preset=session.preset_id,
                outcome=exc.code,
                solved=False,
            )
            if exc.chargeable:
                await self.repository.mark_outcome_unknown(
                    session=session,
                    idempotency_digest=idem_digest,
                    owner=request_id,
                    now=datetime.now(UTC),
                    idempotency_ttl_seconds=self.settings.idempotency_ttl_seconds,
                )
            else:
                await self.repository.release_attempt(
                    session=session, idempotency_digest=idem_digest, owner=request_id
                )
            raise
        finally:
            if inflight_started:
                self.metrics.inflight_provider.labels(preset=session.preset_id).dec()

        completed_at = datetime.now(UTC)
        solved = model_output_solves(expected_proof=proof, model_output=completion.text)
        solved_at = (
            await self.repository.mark_solved(session.session_id, completed_at) if solved else None
        )
        data = AttemptData(
            attempt_id=attempt_id,
            model_response=completion.text,
            solved=solved,
            solved_at=solved_at,
            next_round_hint=(self.settings.next_round_hint.get_secret_value() if solved else None),
            remaining_attempts=reservation.remaining_attempts or 0,
            usage=UsageData(
                input_tokens=completion.input_tokens,
                output_tokens=completion.output_tokens,
            ),
        )
        encrypted = self.replay_crypto.encrypt(
            {"data": data.model_dump(mode="json")},
            associated_data=f"{session_id}:{idem_digest}",
        )
        state = await self.repository.complete_attempt(
            session=session,
            idempotency_digest=idem_digest,
            owner=request_id,
            encrypted_replay=encrypted,
            solved_at=None,
            now=completed_at,
            idempotency_ttl_seconds=self.settings.idempotency_ttl_seconds,
        )
        self.metrics.record_attempt(
            preset=session.preset_id,
            outcome="completed",
            solved=solved,
            input_tokens=completion.input_tokens,
            output_tokens=completion.output_tokens,
        )
        return data.model_copy(update={"remaining_attempts": state.remaining_attempts})

    @staticmethod
    def _raise_for_reservation(status: ReservationStatus) -> None:
        if status is ReservationStatus.RESERVED:
            return
        mapping = {
            ReservationStatus.IDEMPOTENCY_CONFLICT: IdempotencyConflictError,
            ReservationStatus.IN_PROGRESS: AttemptInProgressError,
            ReservationStatus.SESSION_NOT_FOUND: SessionNotFoundError,
            ReservationStatus.SESSION_EXPIRED: SessionExpiredError,
            ReservationStatus.SESSION_SOLVED: SessionSolvedError,
            ReservationStatus.ATTEMPTS_EXHAUSTED: AttemptsExhaustedError,
            ReservationStatus.RATE_LIMITED: RateLimitedError,
            ReservationStatus.PRESET_BUSY: PresetBusyError,
        }
        error = mapping.get(status)
        if error is None:
            raise AttemptInProgressError()
        raise error()
