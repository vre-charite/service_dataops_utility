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

import asyncio

import httpx
import pytest
from faker import Faker
from fakeredis.aioredis import FakeRedis

from app import create_app
from dependencies import Cache


class AsyncClient(httpx.AsyncClient):
    async def delete(self, url: str, **kwds) -> httpx.Response:
        """Default delete request doesn't support body."""

        return await self.request('DELETE', url, **kwds)


@pytest.fixture(scope='session')
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def app(event_loop):
    app = create_app()
    yield app


@pytest.fixture
def fake():
    fake = Faker()
    yield fake


@pytest.fixture
async def client(app) -> AsyncClient:
    async with AsyncClient(app=app, base_url='https://') as client:
        yield client


@pytest.fixture
def redis():
    yield FakeRedis()


@pytest.fixture
def cache(redis):
    yield Cache(redis)
