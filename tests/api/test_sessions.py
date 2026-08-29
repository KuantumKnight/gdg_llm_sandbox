from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx

from app.domain.entities import SessionRecord
from app.repositories.state import RedisStateRepository


async def create_session(client: httpx.AsyncClient) -> dict:
    response = await client.post(
        "/api/v1/sessions",
        headers={"X-Round-Code": "dev-round-access-code"},
        json={"preset_id": "stub-local"},
    )
    assert response.status_code == 201
    return response.json()["data"]


async def test_valid_access_returns_bearer_once_and_authorizes_read(
    client: httpx.AsyncClient,
) -> None:
    created = await create_session(client)

    assert created["session_token"]
    assert created["remaining_attempts"] == 20
    response = await client.get(
        f"/api/v1/sessions/{created['session_id']}",
        headers={"Authorization": f"Bearer {created['session_token']}"},
    )
    assert response.status_code == 200
    read = response.json()["data"]
    assert read["session_token"] is None
    assert read["session_id"] == created["session_id"]


async def test_wrong_round_code_is_generic_and_creates_no_session(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/sessions",
        headers={"X-Round-Code": "wrong"},
        json={"preset_id": "stub-local"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ROUND_ACCESS_DENIED"
    assert "dev-round-access-code" not in response.text


async def test_unknown_preset_and_extra_fields_are_rejected(client: httpx.AsyncClient) -> None:
    unknown = await client.post(
        "/api/v1/sessions",
        headers={"X-Round-Code": "dev-round-access-code"},
        json={"preset_id": "unknown"},
    )
    malformed = await client.post(
        "/api/v1/sessions",
        headers={"X-Round-Code": "dev-round-access-code"},
        json={"preset_id": "stub-local", "provider_url": "http://127.0.0.1"},
    )

    assert unknown.status_code == 404
    assert malformed.status_code == 422
    assert malformed.json()["error"]["code"] == "INVALID_REQUEST"
    assert "provider_url" in malformed.json()["error"]["details"][0]["location"]


async def test_missing_wrong_and_cross_session_bearers_fail(client: httpx.AsyncClient) -> None:
    first = await create_session(client)
    second = await create_session(client)

    missing = await client.get(f"/api/v1/sessions/{first['session_id']}")
    wrong = await client.get(
        f"/api/v1/sessions/{first['session_id']}",
        headers={"Authorization": "Bearer wrong"},
    )
    cross = await client.get(
        f"/api/v1/sessions/{first['session_id']}",
        headers={"Authorization": f"Bearer {second['session_token']}"},
    )

    assert {missing.status_code, wrong.status_code, cross.status_code} == {401}
    assert missing.json()["error"]["code"] == "SESSION_UNAUTHORIZED"


async def test_authenticated_expired_session_returns_gone(
    client: httpx.AsyncClient, repository: RedisStateRepository
) -> None:
    from app.core.security import token_digest

    token = "expired-bearer"
    now = datetime.now(UTC)
    record = SessionRecord(
        session_id="expired-session",
        token_digest=token_digest(token, "dev-session-token-pepper-change-me"),
        preset_id="stub-local",
        created_at=now - timedelta(hours=1),
        expires_at=now - timedelta(seconds=1),
        attempt_limit=20,
    )
    await repository.create_session(record, cleanup_grace_seconds=300)

    response = await client.get(
        "/api/v1/sessions/expired-session",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 410
    assert response.json()["error"]["code"] == "SESSION_EXPIRED"
