"""Request correlation and coarse request-size enforcement."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import cast

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.api.error_handlers import error_response
from app.core.logging import get_logger
from app.core.security import new_request_id
from app.observability.metrics import Metrics


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, body_limit_bytes: int) -> None:
        super().__init__(app)
        self.body_limit_bytes = body_limit_bytes

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        started = perf_counter()
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

        route_object = request.scope.get("route")
        route = getattr(route_object, "path", "unmatched")
        metrics = cast(Metrics, request.app.state.metrics)
        duration = perf_counter() - started
        metrics.record_http(
            route=route,
            method=request.method,
            status=response.status_code,
            duration=duration,
        )
        get_logger().info(
            "http_request",
            extra={
                "request_id": request_id,
                "route": route,
                "method": request.method,
                "status": response.status_code,
                "duration_ms": round(duration * 1000, 3),
            },
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response
