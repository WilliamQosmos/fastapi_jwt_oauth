import pickle

from redis.asyncio import Redis

from app.core.config import settings


class RedisService:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis
        self.ttl = settings.REDIS_TTL

    async def ping(self):
        return await self._redis.ping()

    async def set_cache(self, key: str, value: object, pickle_dump: bool = True):
        if pickle_dump:
            value = pickle.dumps(value)
        return await self._redis.set(key, value, ex=self.ttl)

    async def get_cache(self, key: str, pickle_dump: bool = True) -> object:
        value = await self._redis.get(key)
        if not value:
            return None
        if pickle_dump:
            value = pickle.loads(value)
        return value

    async def delete_cache(self, key: str):
        return await self._redis.delete(key)
