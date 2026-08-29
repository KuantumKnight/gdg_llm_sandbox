from __future__ import annotations

import asyncio
import uuid

import httpx


async def test_concurrent_attempts_only_reserve_one_provider_call(
    client: httpx.AsyncClient,
) -> None:
    created = await client.post(
        "/api/v1/sessions",
        headers={"X-Round-Code": "dev-round-access-code"},
        json={"preset_id": "stub-local"},
    )
    session = created.json()["data"]
    path = f"/api/v1/sessions/{session['session_id']}/attempts"

    async def submit(index: int) -> httpx.Response:
        return await client.post(
            path,
            headers={
                "Authorization": f"Bearer {session['session_token']}",
                "Idempotency-Key": str(uuid.uuid4()),
            },
            json={"prompt": f"ordinary-{index}"},
        )

    responses = await asyncio.gather(*(submit(index) for index in range(5)))

    assert sum(response.status_code == 200 for response in responses) >= 1
    assert all(response.status_code in {200, 409} for response in responses)
