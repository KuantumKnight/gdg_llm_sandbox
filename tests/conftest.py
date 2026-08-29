from __future__ import annotations

from collections.abc import AsyncIterator

import fakeredis.aioredis
import httpx
import pytest

from app.core.config import AppEnvironment, Settings
from app.main import create_app
from app.repositories.redis import Keyspace
from app.repositories.state import RedisStateRepository


@pytest.fixture
def settings() -> Settings:
    return Settings(app_env=AppEnvironment.TEST, _env_file=None)


@pytest.fixture
async def fake_redis() -> AsyncIterator[fakeredis.aioredis.FakeRedis]:
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
def repository(fake_redis: fakeredis.aioredis.FakeRedis) -> RedisStateRepository:
    return RedisStateRepository(fake_redis, keyspace=Keyspace("test-api"))


@pytest.fixture
async def client(
    settings: Settings, repository: RedisStateRepository
) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(settings, repository=repository)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
