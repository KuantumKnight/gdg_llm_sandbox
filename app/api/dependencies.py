"""FastAPI dependencies exposing application-owned services."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Header, Request

from app.core.config import Settings
from app.providers.registry import ProviderRegistry
from app.repositories.state import RedisStateRepository
from app.services.attempts import AttemptService
from app.services.sessions import SessionService


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_repository(request: Request) -> RedisStateRepository:
    return cast(RedisStateRepository, request.app.state.repository)


def get_session_service(
    settings: Annotated[Settings, Depends(get_settings)],
    repository: Annotated[RedisStateRepository, Depends(get_repository)],
) -> SessionService:
    return SessionService(settings=settings, repository=repository)


def get_provider_registry(request: Request) -> ProviderRegistry:
    return cast(ProviderRegistry, request.app.state.provider_registry)


def get_attempt_service(
    settings: Annotated[Settings, Depends(get_settings)],
    repository: Annotated[RedisStateRepository, Depends(get_repository)],
    registry: Annotated[ProviderRegistry, Depends(get_provider_registry)],
) -> AttemptService:
    return AttemptService(settings=settings, repository=repository, provider_registry=registry)


def bearer_token(authorization: Annotated[str | None, Header()] = None) -> str:
    if not authorization:
        return ""
    scheme, _, token = authorization.partition(" ")
    if scheme.casefold() != "bearer" or not token:
        return ""
    return token


SettingsDep = Annotated[Settings, Depends(get_settings)]
RepositoryDep = Annotated[RedisStateRepository, Depends(get_repository)]
SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]
ProviderRegistryDep = Annotated[ProviderRegistry, Depends(get_provider_registry)]
AttemptServiceDep = Annotated[AttemptService, Depends(get_attempt_service)]
BearerDep = Annotated[str, Depends(bearer_token)]
