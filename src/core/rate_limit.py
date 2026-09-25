import time
import uuid

from fastapi import HTTPException, Request, status

from src.core.redis import redis_client


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds

    async def check(self, key: str) -> None:
        now = time.time()
        window_start = now - self.window_seconds

        redis_key = f"rate_limit:{key}"

        async with redis_client.pipeline(transaction=True) as pipe:
            await pipe.zremrangebyscore(
                redis_key,
                0,
                window_start,
            )

            await pipe.zcard(redis_key)

            member = f"{now}:{uuid.uuid4()}"

            await pipe.zadd(
                redis_key,
                {member: now},
            )

            await pipe.expire(
                redis_key,
                self.window_seconds,
            )

            results = await pipe.execute()

        request_count = results[1]

        if request_count >= self.limit:
            retry_after = self.window_seconds

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again later.",
                headers={
                    "Retry-After": str(retry_after),
                },
            )


def get_client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"





LOGIN_LIMITER = RateLimiter(
    limit=5,
    window_seconds=60,
)

REGISTER_LIMITER = RateLimiter(
    limit=5,
    window_seconds=60,
)

RAG_LIMITER = RateLimiter(
    limit=20,
    window_seconds=60,
)

UPLOAD_LIMITER = RateLimiter(
    limit=10,
    window_seconds=60,
)