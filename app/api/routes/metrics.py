"""Authenticated Prometheus scrape endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.dependencies import BearerDep, MetricsDep, SettingsDep
from app.core.security import constant_time_secret_matches
from app.domain.errors import ObservabilityUnauthorizedError

router = APIRouter(tags=["operations"])


@router.get("/metrics", include_in_schema=False)
async def metrics(
    bearer: BearerDep,
    settings: SettingsDep,
    instruments: MetricsDep,
) -> Response:
    expected = settings.observability_token.get_secret_value()
    if not bearer or not constant_time_secret_matches(bearer, expected):
        raise ObservabilityUnauthorizedError()
    return Response(content=generate_latest(instruments.registry), media_type=CONTENT_TYPE_LATEST)
