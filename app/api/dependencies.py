"""FastAPI dependencies exposing application-owned services."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Header, Request

from app.core.config import Settings
from app.repositories.state import RedisStateRepository
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
BearerDep = Annotated[str, Depends(bearer_token)]
