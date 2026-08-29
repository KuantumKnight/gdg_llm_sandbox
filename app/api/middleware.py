"""Request correlation and coarse request-size enforcement."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.api.error_handlers import error_response
from app.core.security import new_request_id


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, body_limit_bytes: int) -> None:
        super().__init__(app)
        self.body_limit_bytes = body_limit_bytes

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        supplied = request.headers.get("X-Request-ID", "")
        try:
            request_id = str(uuid.UUID(supplied))
        except (ValueError, AttributeError):
            request_id = new_request_id()
        request.state.request_id = request_id

        content_length = request.headers.get("content-length")
        try:
            content_size = int(content_length) if content_length else 0
        except ValueError:
            content_size = 0
        response: Response
        if content_size > self.body_limit_bytes:
            response = error_response(
                request,
                status=413,
                code="REQUEST_TOO_LARGE",
                message="The request body is too large.",
                retryable=False,
            )
        else:
            response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
