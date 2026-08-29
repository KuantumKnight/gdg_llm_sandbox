"""Framework-independent errors with stable public codes."""

from __future__ import annotations


class DomainError(Exception):
    code = "DOMAIN_ERROR"
    retryable = False


class StateUnavailableError(DomainError):
    code = "STATE_UNAVAILABLE"
    retryable = True


class RoundAccessDeniedError(DomainError):
    code = "ROUND_ACCESS_DENIED"


class PresetNotAvailableError(DomainError):
    code = "PRESET_NOT_AVAILABLE"


class PromptTooLargeError(DomainError):
    code = "PROMPT_TOO_LARGE"


class ObservabilityUnauthorizedError(DomainError):
    code = "OBSERVABILITY_UNAUTHORIZED"


class SessionNotFoundError(DomainError):
    code = "SESSION_UNAUTHORIZED"


class SessionExpiredError(DomainError):
    code = "SESSION_EXPIRED"


class SessionSolvedError(DomainError):
    code = "SESSION_ALREADY_SOLVED"


class AttemptsExhaustedError(DomainError):
    code = "ATTEMPTS_EXHAUSTED"


class AttemptInProgressError(DomainError):
    code = "ATTEMPT_IN_PROGRESS"
    retryable = True


class IdempotencyConflictError(DomainError):
    code = "IDEMPOTENCY_KEY_REUSED"


class RateLimitedError(DomainError):
    code = "RATE_LIMITED"
    retryable = True


class PresetBusyError(DomainError):
    code = "PROVIDER_BUSY"
    retryable = True
