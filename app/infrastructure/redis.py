from redis.asyncio import Redis
from app.config import settings


redis_client = Redis.from_url(
    settings.redis_url,
    decode_responses=True,
)


async def cache_get(key: str) -> str | None:
    """Cache read tolerante: si Redis no esta disponible, devueve miss."""
    try:
        return await redis_client.get(key)
    except Exception:
        return None


async def cache_set(key: str, value: str, ttl: int) -> None:
    """Cache write tolerante: falla silenciosamente si Redis no responde."""
    try:
        await redis_client.set(key, value, ex=ttl)
    except Exception:
        pass


async def cache_incr_with_ttl(key: str, ttl: int) -> int:
    """INCR + EXPIRE en la primera unidad. Devuelve el conteo o -1 si falla."""
    try:
        count = await redis_client.incr(key)
        if count == 1:
            await redis_client.expire(key, ttl)
        return count
    except Exception:
        return -1


async def cache_get_str(key: str) -> str | None:
    return await cache_get(key)


async def cache_set_str(key: str, value: str, ttl: int) -> None:
    await cache_set(key, value, ttl)


async def cache_expire(key: str, ttl: int) -> None:
    try:
        await redis_client.expire(key, ttl)
    except Exception:
        pass