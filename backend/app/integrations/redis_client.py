from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis


def get_redis(request: Request) -> Redis:
    client: Redis | None = getattr(request.app.state, "redis", None)
    if client is None:
        raise RuntimeError("Redis client is not initialized")
    return client


RedisDep = Annotated[Redis, Depends(get_redis)]
