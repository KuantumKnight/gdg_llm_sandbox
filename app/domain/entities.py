"""Immutable value objects shared by application services and adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ChallengeMessages:
    system: str
    user: str


@dataclass(frozen=True, slots=True)
class CompletionResult:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    provider_request_id: str | None = None


@dataclass(frozen=True, slots=True)
class SessionRecord:
    session_id: str
    token_digest: str
    preset_id: str
    created_at: datetime
    expires_at: datetime
    attempt_limit: int
    charged_attempts: int = 0
    solved_at: datetime | None = None
    prompt_version: str = "gatekeeper-v1"

    @property
    def remaining_attempts(self) -> int:
        return max(0, self.attempt_limit - self.charged_attempts)
