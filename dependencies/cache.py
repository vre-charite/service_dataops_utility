# Copyright 2022 Indoc Research
# 
# Licensed under the EUPL, Version 1.2 or – as soon they
# will be approved by the European Commission - subsequent
# versions of the EUPL (the "Licence");
# You may not use this work except in compliance with the
# Licence.
# You may obtain a copy of the Licence at:
# 
# https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12
# 
# Unless required by applicable law or agreed to in
# writing, software distributed under the Licence is
# distributed on an "AS IS" basis,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied.
# See the Licence for the specific language governing
# permissions and limitations under the Licence.
# 

from typing import Optional
from typing import Union

from aioredis.client import Redis
from fastapi import Depends

from config import Settings
from config import get_settings


class GetRedis:
    """Create a FastAPI callable dependency for Redis single instance."""

    def __init__(self) -> None:
        self.instance = None

    async def __call__(self, settings: Settings = Depends(get_settings)) -> Redis:
        """Return an instance of Redis class."""

        if not self.instance:
            self.instance = Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
            )
        return self.instance


get_redis = GetRedis()


class Cache:
    """Manage cache entries."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def set(self, key: str, value: Union[str, bytes]) -> bool:
        """Set the value for the key."""

        return await self.redis.set(key, value)

    async def get(self, key: str) -> Optional[bytes]:
        """Return the value for the key or None if the key doesn't exist."""

        return await self.redis.get(key)

    async def delete(self, key: str) -> bool:
        """Delete the value for the key.

        Return true if the key existed before the removal.
        """

        return bool(await self.redis.delete(key))

    async def is_exist(self, key: str) -> bool:
        """Return true if the value for the key exists."""

        return bool(await self.redis.exists(key))


async def get_cache(redis: Redis = Depends(get_redis)) -> Cache:
    """Return an instance of Cache class."""

    return Cache(redis)
