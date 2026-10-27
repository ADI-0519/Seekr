import json

import redis.asyncio as redis

from app.core.config import get_settings

settings = get_settings()
_client = None


# Establish and return a singleton asynchronous connection to the Redis server
async def get_redis():
    global _client
    if not _client:
        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client


# Safely terminate the Redis connection pool
async def close_redis():
    global _client
    if _client:
        await _client.close()
        _client = None


# Service class to handle data caching and retrieval operations
class CacheService:
    STATUS_TTL = 300
    SEARCH_TTL = 300

    def __init__(self, client):
        self.r = client

    async def get_status(self, video_id: int):
        data = await self.r.get(f"video:{video_id}:status")
        return json.loads(data) if data else None

    async def set_status(self, video_id: int, status: str, error=None):
        key = f"video:{video_id}:status"
        await self.r.setex(key, self.STATUS_TTL, json.dumps({"status": status, "error": error}))

    async def clear_status(self, video_id: int):
        await self.r.delete(f"video:{video_id}:status")

    async def get(self, key: str):
        data = await self.r.get(key)
        return json.loads(data) if data else None

    async def set(self, key: str, val, ttl: int):
        await self.r.setex(key, ttl, json.dumps(val))
