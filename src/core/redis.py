import redis.asyncio as redis
import asyncio

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True,
)


async def close_redis():
    await redis_client.close()

if __name__=="__main__":
    asyncio.run(close_redis())





