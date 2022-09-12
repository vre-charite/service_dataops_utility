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

import pytest
from aioredis import Redis

from config import get_settings
from dependencies import Cache
from dependencies import get_cache
from dependencies.cache import GetRedis


@pytest.fixture
def get_redis():
    yield GetRedis()


class TestGetRedis:
    async def test_instance_has_uninitialized_instance_attribute_after_creation(self, get_redis):
        assert get_redis.instance is None

    async def test_call_returns_an_instance_of_redis(self, get_redis):
        redis = await get_redis(settings=get_settings())
        assert redis is get_redis.instance
        assert isinstance(redis, Redis)


class TestCache:
    async def test_get_cache_returns_an_instance_of_cache(self, redis):
        cache = await get_cache(redis=redis)
        assert isinstance(cache, Cache)

    async def test_set_stores_value_by_key(self, fake, cache):
        key = fake.pystr()
        value = fake.binary(10)

        result = await cache.set(key, value)
        assert result is True

        result = await cache.get(key)
        assert result == value

    async def test_get_returns_value_by_key(self, fake, cache):
        key = fake.pystr()
        value = fake.binary(10)
        await cache.set(key, value)

        result = await cache.get(key)
        assert result == value

    async def test_get_returns_none_if_key_does_not_exist(self, fake, cache):
        key = fake.pystr()

        result = await cache.get(key)
        assert result is None

    async def test_delete_removes_value_by_key(self, fake, cache):
        key = fake.pystr()
        value = fake.pystr()
        await cache.set(key, value)

        result = await cache.delete(key)
        assert result is True

        result = await cache.get(key)
        assert result is None

    async def test_delete_returns_false_if_key_did_not_exist(self, fake, cache):
        key = fake.pystr()

        result = await cache.delete(key)
        assert result is False

    async def test_is_exist_returns_true_if_key_exists(self, fake, cache):
        key = fake.pystr()
        value = fake.pystr()
        await cache.set(key, value)

        result = await cache.is_exist(key)
        assert result is True

    async def test_is_exist_returns_false_if_key_does_not_exist(self, fake, cache):
        key = fake.pystr()

        result = await cache.is_exist(key)
        assert result is False
