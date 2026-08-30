"""ASGI application entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.error_handlers import install_error_handlers
from app.api.middleware import RequestContextMiddleware
from app.api.routes.attempts import router as attempts_router
from app.api.routes.config import router as config_router
from app.api.routes.health import router as health_router
from app.api.routes.metrics import router as metrics_router
from app.api.routes.sessions import router as sessions_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.observability.metrics import Metrics
from app.providers.registry import ProviderRegistry
from app.repositories.redis import Keyspace, create_redis_client
from app.repositories.state import RedisStateRepository

WEB_DIRECTORY = Path(__file__).resolve().parent / "web"


def create_app(
    settings: Settings | None = None,
    *,
    repository: RedisStateRepository | None = None,
) -> FastAPI:
    """Create an application instance with explicit, testable settings."""
    resolved = settings or get_settings()
    owns_repository = repository is None
    configure_logging(
        level=resolved.log_level,
        secrets=[
            resolved.redis_url.get_secret_value(),
            resolved.round_access_code.get_secret_value(),
            resolved.session_token_pepper.get_secret_value(),
            resolved.proof_derivation_secret.get_secret_value(),
            resolved.idempotency_digest_secret.get_secret_value(),
            resolved.replay_encryption_key.get_secret_value(),
            resolved.next_round_hint.get_secret_value(),
            resolved.observability_token.get_secret_value(),
            *[
                preset.server_api_key.get_secret_value()
                for preset in resolved.provider_presets
                if preset.server_api_key is not None
            ],
        ],
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        if repository is None:
            client = create_redis_client(resolved.redis_url.get_secret_value())
            application.state.repository = RedisStateRepository(
                client, keyspace=Keyspace(resolved.app_env.value)
            )
        else:
            application.state.repository = repository
        yield
        if owns_repository:
            await application.state.repository.close()

    app = FastAPI(
        title=resolved.app_name,
        version=__version__,
        description=(
            "API-first prompt-injection challenge. Attack the model instructions, "
            "not the service infrastructure."
        ),
        lifespan=lifespan,
    )
    app.state.settings = resolved
    app.state.metrics = Metrics()
    app.state.provider_registry = ProviderRegistry(resolved)
    if repository is not None:
        app.state.repository = repository

    app.add_middleware(RequestContextMiddleware, body_limit_bytes=resolved.request_body_limit_bytes)
    if resolved.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=resolved.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                "Idempotency-Key",
                "X-Provider-API-Key",
                "X-Request-ID",
                "X-Round-Code",
            ],
        )

    install_error_handlers(app)
    app.include_router(config_router)
    app.include_router(sessions_router)
    app.include_router(attempts_router)
    app.include_router(health_router)
    app.include_router(metrics_router)
    app.mount("/static", StaticFiles(directory=WEB_DIRECTORY), name="static")

    @app.get("/", include_in_schema=False)
    async def root() -> FileResponse:
        return FileResponse(
            WEB_DIRECTORY / "index.html",
            media_type="text/html",
            headers={"Cache-Control": "no-cache"},
        )

    return app


app = create_app()
