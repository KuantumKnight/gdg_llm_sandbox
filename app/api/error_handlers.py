"""Stable public error envelopes independent of internal exceptions."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain.errors import (
    AttemptInProgressError,
    AttemptsExhaustedError,
    DomainError,
    IdempotencyConflictError,
    PresetBusyError,
    PresetNotAvailableError,
    PromptTooLargeError,
    RateLimitedError,
    RoundAccessDeniedError,
    SessionExpiredError,
    SessionNotFoundError,
    SessionSolvedError,
    StateUnavailableError,
)
from app.providers.errors import (
    ProviderConfigurationError,
    ProviderCredentialRejectedError,
    ProviderCredentialRequiredError,
    ProviderError,
    ProviderMalformedResponseError,
    ProviderRateLimitedError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)


@dataclass(frozen=True, slots=True)
class ErrorPresentation:
    status: int
    message: str


_PRESENTATIONS: dict[type[DomainError], ErrorPresentation] = {
    RoundAccessDeniedError: ErrorPresentation(403, "Round access was denied."),
    PresetNotAvailableError: ErrorPresentation(404, "The selected provider preset is unavailable."),
    PromptTooLargeError: ErrorPresentation(
        422, "The prompt exceeds the published character limit."
    ),
    SessionNotFoundError: ErrorPresentation(401, "Session authorization is invalid."),
    SessionExpiredError: ErrorPresentation(410, "This challenge session has expired."),
    SessionSolvedError: ErrorPresentation(409, "This challenge session is already solved."),
    AttemptsExhaustedError: ErrorPresentation(429, "This session has no attempts remaining."),
    AttemptInProgressError: ErrorPresentation(409, "Another attempt is already in progress."),
    IdempotencyConflictError: ErrorPresentation(
        409, "This idempotency key was used for another request."
    ),
    RateLimitedError: ErrorPresentation(429, "Too many requests. Retry later."),
    PresetBusyError: ErrorPresentation(503, "The selected provider is temporarily busy."),
    StateUnavailableError: ErrorPresentation(503, "Shared challenge state is unavailable."),
}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        presentation = _PRESENTATIONS.get(
            type(exc), ErrorPresentation(500, "The request could not be completed.")
        )
        return error_response(
            request,
            status=presentation.status,
            code=exc.code,
            message=presentation.message,
            retryable=exc.retryable,
        )

    @app.exception_handler(ProviderError)
    async def provider_error_handler(request: Request, exc: ProviderError) -> JSONResponse:
        status, message = _provider_presentation(exc)
        return error_response(
            request,
            status=status,
            code=exc.code,
            message=message,
            retryable=exc.retryable,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {"location": ".".join(str(part) for part in error["loc"]), "type": error["type"]}
            for error in exc.errors()
        ]
        return error_response(
            request,
            status=422,
            code="INVALID_REQUEST",
            message="The request did not match the API contract.",
            retryable=False,
            details=details,
        )


def error_response(
    request: Request,
    *,
    status: int,
    code: str,
    message: str,
    retryable: bool,
    retry_after_seconds: int | None = None,
    details: list[dict[str, str]] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    headers = {}
    if retry_after_seconds is not None:
        headers["Retry-After"] = str(retry_after_seconds)
    return JSONResponse(
        status_code=status,
        headers=headers,
        content={
            "error": {
                "code": code,
                "message": message,
                "retryable": retryable,
                "request_id": request_id,
                "retry_after_seconds": retry_after_seconds,
                "details": details or [],
            }
        },
    )


def _provider_presentation(exc: ProviderError) -> tuple[int, str]:
    if isinstance(exc, ProviderCredentialRequiredError):
        return 422, "This provider preset requires a participant API key."
    if isinstance(exc, ProviderCredentialRejectedError):
        return 422, "The provider rejected the supplied credential."
    if isinstance(exc, ProviderConfigurationError):
        return 503, "The selected provider preset is unavailable."
    if isinstance(exc, ProviderRateLimitedError):
        return 503, "The provider is temporarily rate limited."
    if isinstance(exc, ProviderTimeoutError):
        return 504, "The provider response timed out; the attempt outcome may be unknown."
    if isinstance(exc, ProviderMalformedResponseError):
        return 502, "The provider returned an unusable response."
    if isinstance(exc, ProviderUnavailableError):
        return 503, "The provider is temporarily unavailable."
    return 503, "The provider request failed."
