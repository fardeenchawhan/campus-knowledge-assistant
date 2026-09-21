import redis.asyncio as redis

from src.core.config import settings


redis_client = redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)


async def close_redis():
    await redis_client.aclose()





