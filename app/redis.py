import redis.asyncio as redis
from app.core.config import get_settings
from typing import Optional, Union, Any
import logging

try:
    from upstash_redis import Redis as UpstashRedis
except ImportError:
    UpstashRedis = None
    logging.warning(
        "upstash_redis package not installed. "
        "To use Upstash Redis REST API, install with: pip install upstash-redis"
    )

settings = get_settings()

if settings.USE_REDIS_REST_API and UpstashRedis is not None:
    redis_client = UpstashRedis(
        url=settings.UPSTASH_REDIS_REST_URL,
        token=settings.UPSTASH_REDIS_REST_TOKEN
    )

    class AsyncRedisWrapper:
        def __init__(self, upstash_client):
            self.client = upstash_client

        async def get(self, key: str) -> Optional[str]:
            return self.client.get(key)

        async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
            if ex is not None:
                return self.client.set(key, value, ex=ex)
            return self.client.set(key, value)

        async def delete(self, key: str) -> int:
            return self.client.delete(key)

    async_redis_client = AsyncRedisWrapper(redis_client)

else:
    redis_client = redis.from_url(settings.REDIS_URL)
    async_redis_client = redis_client