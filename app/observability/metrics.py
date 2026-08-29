"""Low-cardinality Prometheus instruments."""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram


class Metrics:
    def __init__(self) -> None:
        self.registry = CollectorRegistry(auto_describe=True)
        self.http_requests = Counter(
            "sandbox_http_requests_total",
            "HTTP requests by route template and status",
            ("route", "method", "status"),
            registry=self.registry,
        )
        self.http_duration = Histogram(
            "sandbox_http_request_duration_seconds",
            "HTTP request duration by route template and method",
            ("route", "method"),
            registry=self.registry,
        )
        self.sessions_created = Counter(
            "sandbox_sessions_created_total",
            "Challenge sessions created by configured preset",
            ("preset",),
            registry=self.registry,
        )
        self.attempts = Counter(
            "sandbox_attempts_total",
            "Attempts by preset, outcome, and solve state",
            ("preset", "outcome", "solved"),
            registry=self.registry,
        )
        self.provider_tokens = Counter(
            "sandbox_provider_tokens_total",
            "Provider tokens by preset and direction",
            ("preset", "direction"),
            registry=self.registry,
        )
        self.idempotency_replays = Counter(
            "sandbox_idempotency_replays_total",
            "Idempotency lookups served from replay",
            registry=self.registry,
        )
        self.inflight_provider = Gauge(
            "sandbox_inflight_provider_requests",
            "Provider requests currently in progress",
            ("preset",),
            registry=self.registry,
        )

    def record_http(self, *, route: str, method: str, status: int, duration: float) -> None:
        self.http_requests.labels(route=route, method=method, status=str(status)).inc()
        self.http_duration.labels(route=route, method=method).observe(duration)

    def record_attempt(
        self,
        *,
        preset: str,
        outcome: str,
        solved: bool,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ) -> None:
        self.attempts.labels(preset=preset, outcome=outcome, solved=str(solved).lower()).inc()
        if input_tokens is not None:
            self.provider_tokens.labels(preset=preset, direction="input").inc(input_tokens)
        if output_tokens is not None:
            self.provider_tokens.labels(preset=preset, direction="output").inc(output_tokens)
