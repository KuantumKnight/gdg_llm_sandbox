from __future__ import annotations

import httpx


async def test_security_headers_and_api_no_store(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/config")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
    assert response.headers["cross-origin-opener-policy"] == "same-origin"
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["cache-control"] == "no-store"


async def test_oversized_body_is_rejected_before_parsing(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/sessions",
        headers={"Content-Length": "20000", "X-Round-Code": "dev-round-access-code"},
        content=b"{}",
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"


async def test_docs_csp_allows_only_required_swagger_assets(client: httpx.AsyncClient) -> None:
    response = await client.get("/docs")

    assert response.status_code == 200
    policy = response.headers["content-security-policy"]
    assert "https://cdn.jsdelivr.net" in policy
    assert "https://fastapi.tiangolo.com" in policy
    assert "frame-ancestors 'none'" in policy


async def test_cors_is_closed_by_default(client: httpx.AsyncClient) -> None:
    response = await client.options(
        "/api/v1/config",
        headers={
            "Origin": "https://attacker.invalid",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-origin" not in response.headers
