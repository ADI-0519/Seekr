import json
from unittest.mock import AsyncMock

import pytest
from app.services.cache import CacheService


@pytest.mark.asyncio
async def test_status_roundtrip_and_clear():
    redis_client = AsyncMock()
    svc = CacheService(redis_client)

    await svc.set_status(12, "processing", error="none")

    redis_client.setex.assert_awaited_once()
    key, ttl, payload = redis_client.setex.await_args.args
    assert key == "video:12:status"
    assert ttl == svc.STATUS_TTL
    assert json.loads(payload) == {"status": "processing", "error": "none"}

    redis_client.get.return_value = payload
    got = await svc.get_status(12)
    assert got == {"status": "processing", "error": "none"}

    await svc.clear_status(12)
    redis_client.delete.assert_awaited_once_with("video:12:status")


@pytest.mark.asyncio
async def test_generic_get_set_handles_missing_values():
    redis_client = AsyncMock()
    svc = CacheService(redis_client)

    await svc.set("search:key", {"x": 1}, ttl=42)
    redis_client.setex.assert_awaited_once()
    args = redis_client.setex.await_args.args
    assert args[0] == "search:key"
    assert args[1] == 42
    assert json.loads(args[2]) == {"x": 1}

    redis_client.get.return_value = None
    assert await svc.get("search:key") is None

    redis_client.get.return_value = json.dumps([1, 2, 3])
    assert await svc.get("search:key") == [1, 2, 3]
