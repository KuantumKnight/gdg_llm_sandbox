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
    RateLimitedError,
    RoundAccessDeniedError,
    SessionExpiredError,
    SessionNotFoundError,
    SessionSolvedError,
    StateUnavailableError,
)


@dataclass(frozen=True, slots=True)
class ErrorPresentation:
    status: int
    message: str


_PRESENTATIONS: dict[type[DomainError], ErrorPresentation] = {
    RoundAccessDeniedError: ErrorPresentation(403, "Round access was denied."),
    PresetNotAvailableError: ErrorPresentation(404, "The selected provider preset is unavailable."),
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
