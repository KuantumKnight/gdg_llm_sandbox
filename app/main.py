"""ASGI application entry point."""

from fastapi import FastAPI

from app import __version__
from app.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an application instance with explicit, testable settings."""
    resolved = settings or get_settings()
    app = FastAPI(
        title=resolved.app_name,
        version=__version__,
        description=(
            "API-first prompt-injection challenge. Attack the model instructions, "
            "not the service infrastructure."
        ),
    )
    app.state.settings = resolved

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {"service": resolved.app_name, "version": __version__}

    return app


app = create_app()
