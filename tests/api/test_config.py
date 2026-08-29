from __future__ import annotations

import httpx


async def test_public_config_exposes_only_safe_preset_fields(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/config")

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["round_status"] == "open"
    assert body["presets"][0]["id"] == "stub-local"
    serialized = response.text
    assert "server_api_key" not in serialized
    assert "dev-provider-key" not in serialized
    assert "stub.invalid" not in serialized
    assert "next_round_hint" not in serialized


async def test_request_id_is_returned_and_invalid_value_replaced(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/api/v1/config", headers={"X-Request-ID": "not-a-uuid"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "not-a-uuid"
    assert len(response.headers["X-Request-ID"]) == 36
