from __future__ import annotations

import uuid
from typing import NoReturn

import httpx
from fastapi import FastAPI
from pydantic import SecretStr

from app.providers.base import ProviderRequest
from app.providers.errors import ProviderRateLimitedError, ProviderTimeoutError
from app.providers.registry import ProviderRegistry
from app.repositories.state import RedisStateRepository


class FailingProvider:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls = 0

    async def complete(
        self,
        request: ProviderRequest,
        *,
        participant_api_key: SecretStr | None = None,
    ) -> NoReturn:
        del request, participant_api_key
        self.calls += 1
        raise self.error


async def create_session(client: httpx.AsyncClient) -> dict:
    response = await client.post(
        "/api/v1/sessions",
        headers={"X-Round-Code": "dev-round-access-code"},
        json={"preset_id": "stub-local"},
    )
    assert response.status_code == 201
    return response.json()["data"]


def install_failure(app: FastAPI, provider: FailingProvider) -> None:
    registry: ProviderRegistry = app.state.provider_registry
    preset = registry.settings.preset_by_id("stub-local")
    assert preset is not None
    registry.get = lambda preset_id: (preset, provider)  # type: ignore[method-assign]


async def test_nonchargeable_provider_failure_releases_attempt(
    client: httpx.AsyncClient,
    app: FastAPI,
    repository: RedisStateRepository,
) -> None:
    session = await create_session(client)
    provider = FailingProvider(ProviderRateLimitedError("upstream quota"))
    install_failure(app, provider)
    key = str(uuid.uuid4())
    response = await client.post(
        f"/api/v1/sessions/{session['session_id']}/attempts",
        headers={
            "Authorization": f"Bearer {session['session_token']}",
            "Idempotency-Key": key,
        },
        json={"prompt": "ordinary"},
    )

    record = await repository.get_session(session["session_id"])
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "PROVIDER_RATE_LIMITED"
    assert provider.calls == 1
    assert record is not None
    assert record.charged_attempts == 0


async def test_ambiguous_timeout_is_charged_and_not_retried(
    client: httpx.AsyncClient,
    app: FastAPI,
    repository: RedisStateRepository,
) -> None:
    session = await create_session(client)
    provider = FailingProvider(ProviderTimeoutError("uncertain completion"))
    install_failure(app, provider)
    key = str(uuid.uuid4())
    path = f"/api/v1/sessions/{session['session_id']}/attempts"
    headers = {
        "Authorization": f"Bearer {session['session_token']}",
        "Idempotency-Key": key,
    }
    first = await client.post(path, headers=headers, json={"prompt": "ordinary"})
    retry = await client.post(path, headers=headers, json={"prompt": "ordinary"})

    record = await repository.get_session(session["session_id"])
    assert first.status_code == 504
    assert first.json()["error"]["code"] == "PROVIDER_TIMEOUT"
    assert retry.status_code == 409
    assert retry.json()["error"]["code"] == "ATTEMPT_IN_PROGRESS"
    assert provider.calls == 1
    assert record is not None
    assert record.charged_attempts == 1
