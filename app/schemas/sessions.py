from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.config import CredentialMode
from app.domain.entities import SessionRecord


class CreateSessionRequest(BaseModel):
    model_config = {"extra": "forbid"}

    preset_id: str = Field(min_length=2, max_length=63, pattern=r"^[a-z0-9][a-z0-9-]+$")


class SessionData(BaseModel):
    session_id: str
    session_token: str | None = None
    preset_id: str
    model_label: str
    credential_mode: CredentialMode
    created_at: datetime
    expires_at: datetime
    attempt_limit: int
    remaining_attempts: int
    solved: bool
    solved_at: datetime | None = None
    next_round_hint: str | None = None

    @classmethod
    def from_record(
        cls,
        record: SessionRecord,
        *,
        model_label: str,
        credential_mode: CredentialMode,
        session_token: str | None = None,
        next_round_hint: str | None = None,
    ) -> SessionData:
        return cls(
            session_id=record.session_id,
            session_token=session_token,
            preset_id=record.preset_id,
            model_label=model_label,
            credential_mode=credential_mode,
            created_at=record.created_at,
            expires_at=record.expires_at,
            attempt_limit=record.attempt_limit,
            remaining_attempts=record.remaining_attempts,
            solved=record.solved_at is not None,
            solved_at=record.solved_at,
            next_round_hint=next_round_hint,
        )


class SessionEnvelope(BaseModel):
    data: SessionData
