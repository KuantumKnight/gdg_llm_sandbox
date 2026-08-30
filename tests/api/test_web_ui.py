from __future__ import annotations

import httpx


async def test_root_serves_participant_ui(client: httpx.AsyncClient) -> None:
    response = await client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"] == "no-cache"
    assert "GDG LLM Sandbox" in response.text
    assert "Break the gatekeeper." in response.text
    assert 'id="admission-form"' in response.text
    assert 'id="prompt-form"' in response.text
    assert 'href="/static/favicon.svg"' in response.text
    assert 'href="/static/styles.css"' in response.text
    assert 'src="/static/app.js"' in response.text
    assert "dev-round-access-code" not in response.text
    assert "dev-provider-key" not in response.text


async def test_ui_assets_are_served_with_security_headers(client: httpx.AsyncClient) -> None:
    stylesheet = await client.get("/static/styles.css")
    script = await client.get("/static/app.js")
    favicon = await client.get("/static/favicon.svg")

    assert stylesheet.status_code == 200
    assert stylesheet.headers["content-type"].startswith("text/css")
    assert "prefers-reduced-motion" in stylesheet.text
    assert script.status_code == 200
    assert "javascript" in script.headers["content-type"]
    assert "Content-Security-Policy" in script.headers
    assert "sessionStorage" not in script.text
    assert "state.token = session.session_token" in script.text
    assert favicon.status_code == 200
    assert favicon.headers["content-type"].startswith("image/svg+xml")


async def test_ui_copy_has_no_forbidden_dash_characters(client: httpx.AsyncClient) -> None:
    response = await client.get("/")

    assert "\N{EM DASH}" not in response.text
    assert "\N{EN DASH}" not in response.text
