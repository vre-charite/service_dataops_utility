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


@pytest.mark.parametrize('operation', ['read', 'write'])
async def test_lock(client, fake, operation):
    payload = {
        'resource_key': fake.pystr(),
        'operation': operation,
    }

    response = await client.post('/v2/resource/lock/', json=payload)
    assert response.status_code == 200

    response = await client.delete('/v2/resource/lock/', json=payload)
    assert response.status_code == 200


@pytest.mark.parametrize('operation', ['read', 'write'])
async def test_bulk_lock_performs_lock_for_multiple_keys(client, fake, operation):
    key1 = f'a_{fake.pystr()}'
    key2 = f'b_{fake.pystr()}'
    payload = {
        'resource_keys': [key1, key2],
        'operation': operation,
    }

    response = await client.post('/v2/resource/lock/bulk', json=payload)
    assert response.status_code == 200

    expected_result = [
        [key1, True],
        [key2, True],
    ]
    result = response.json()['result']

    assert expected_result == result


@pytest.mark.parametrize('operation', ['read', 'write'])
async def test_bulk_lock_stops_locking_when_lock_attempt_fails(client, fake, operation):
    key1 = f'a_{fake.pystr()}'
    key2 = f'b_{fake.pystr()}'
    key3 = f'c_{fake.pystr()}'

    await client.post('/v2/resource/lock/', json={'resource_key': key2, 'operation': 'write'})

    payload = {
        'resource_keys': [key1, key2, key3],
        'operation': operation,
    }

    response = await client.post('/v2/resource/lock/bulk', json=payload)
    assert response.status_code == 409

    expected_result = [
        [key1, True],
        [key2, False],
        [key3, False],
    ]
    result = response.json()['result']

    assert expected_result == result


@pytest.mark.parametrize('operation', ['read', 'write'])
async def test_bulk_unlock_performs_unlock_for_multiple_keys(client, fake, operation):
    key1 = f'a_{fake.pystr()}'
    key2 = f'b_{fake.pystr()}'

    for key in [key1, key2]:
        await client.post('/v2/resource/lock/', json={'resource_key': key, 'operation': 'write'})

    payload = {
        'resource_keys': [key1, key2],
        'operation': operation,
    }

    response = await client.delete('/v2/resource/lock/bulk', json=payload)
    assert response.status_code == 200

    expected_result = [
        [key1, True],
        [key2, True],
    ]
    result = response.json()['result']

    assert expected_result == result


@pytest.mark.parametrize('operation', ['read', 'write'])
async def test_bulk_unlock_continues_unlocking_when_unlock_attempt_fails(client, fake, operation):
    key1 = f'a_{fake.pystr()}'
    key2 = f'b_{fake.pystr()}'

    await client.post('/v2/resource/lock/', json={'resource_key': key2, 'operation': 'write'})

    payload = {
        'resource_keys': [key1, key2],
        'operation': operation,
    }

    response = await client.delete('/v2/resource/lock/bulk', json=payload)
    assert response.status_code == 400

    expected_result = [
        [key1, False],
        [key2, True],
    ]
    result = response.json()['result']

    assert expected_result == result


@pytest.mark.parametrize('operation', ['read', 'write'])
async def test_lock_returns_404_for_not_existing_lock(client, fake, operation):
    payload = {
        'resource_key': fake.pystr(),
        'operation': operation,
    }

    response = await client.delete('/v2/resource/lock/', json=payload)
    assert response.status_code == 400


async def test_read_lock_not_exist_after_multiple_lock_unlock_operations(client, fake):
    payload = {
        'resource_key': fake.pystr(),
        'operation': 'read',
    }

    num = 10
    for _ in range(num):
        response = await client.post('/v2/resource/lock/', json=payload)
        assert response.status_code == 200

    for _ in range(num):
        response = await client.delete('/v2/resource/lock/', json=payload)
        assert response.status_code == 200

    response = await client.get('/v2/resource/lock/', params=payload)
    status = response.json()['result']['status']
    assert status is None


async def test_second_write_lock_is_not_allowed_and_returns_409(client, fake):
    payload = {
        'resource_key': fake.pystr(),
        'operation': 'write',
    }

    response = await client.post('/v2/resource/lock/', json=payload)
    assert response.status_code == 200

    response = await client.post('/v2/resource/lock/', json=payload)
    assert response.status_code == 409
