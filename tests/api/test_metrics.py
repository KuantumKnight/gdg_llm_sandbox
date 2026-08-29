from __future__ import annotations

import httpx


async def test_metrics_requires_observability_bearer(client: httpx.AsyncClient) -> None:
    missing = await client.get("/metrics")
    wrong = await client.get("/metrics", headers={"Authorization": "Bearer incorrect"})

    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "OBSERVABILITY_UNAUTHORIZED"
    assert wrong.status_code == 401


async def test_metrics_exposes_only_bounded_operational_labels(
    client: httpx.AsyncClient,
) -> None:
    await client.get("/api/v1/config")
    response = await client.get(
        "/metrics",
        headers={"Authorization": "Bearer dev-observability-token-change-me"},
    )

    assert response.status_code == 200
    assert "sandbox_http_requests_total" in response.text
    assert 'route="/api/v1/config"' in response.text
    assert "dev-observability-token-change-me" not in response.text
    assert "prompt" not in response.text.casefold()
