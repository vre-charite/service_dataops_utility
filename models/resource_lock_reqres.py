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

from enum import Enum
from enum import unique
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from pydantic import BaseModel
from pydantic import Field

from models.base_models import APIResponse
from resources.redis import SrvAioRedisSingleton


class EResourceLockStatus(Enum):
    LOCKED = 10
    UNLOCKED = 20


@unique
class ResourceLockOperation(str, Enum):
    READ = 'read'
    WRITE = 'write'

    class Config:
        use_enum_values = True


class ResourceLockRequestBody(BaseModel):
    resource_key: str = Field(description='An identity key to mark the locked resource, can be path, geid, guid')
    operation: ResourceLockOperation


class ResourceLockBulkRequestBody(BaseModel):
    resource_keys: List[str] = Field(
        description='A list of identity keys to mark the locked resource, can be path, geid, guid'
    )
    operation: ResourceLockOperation


class ResourceLockResponseResult(BaseModel):
    key: str
    status: Optional[str]


class ResourceLockResponse(APIResponse):
    result: ResourceLockResponseResult


class ResourceLockBulkResponse(APIResponse):
    result: List[Tuple[str, bool]]


class RLockPOST(BaseModel):
    resource_key: str = Field(description='An identity key to mark the locked resource, can be path, geid, guid')
    sub_key: str = 'default'


class RLockResponse(APIResponse):
    result: Dict[str, str] = Field(
        {},
        example={
            'key': 'str',
            'status': 'LOCKED',
        },
    )


class RLockClearResponse(APIResponse):
    result: Dict[str, str] = Field(
        {},
        example={
            'key': 'all',
            'status': 'UNLOCKED',
        },
    )


class ResourceLockManager:
    def __init__(self):
        self.__srv_redis = SrvAioRedisSingleton()

    async def lock(self, key, sub_key):
        lock_key = 'RLOCK:{}:{}'.format(key, sub_key)
        await self.__srv_redis.set_by_key(lock_key, EResourceLockStatus.LOCKED.name)

    async def unlock(self, key, sub_key):
        lock_key = 'RLOCK:{}:{}'.format(key, sub_key)
        await self.__srv_redis.delete_by_key(lock_key)

    async def unlink(self, key, sub_key):
        lock_key = 'RLOCK:{}:{}'.format(key, sub_key)
        await self.__srv_redis.unlink_by_key(lock_key)

    async def check_lock(self, key, sub_key):
        lock_key = 'RLOCK:{}:{}'.format(key, sub_key)
        record = await self.__srv_redis.get_by_key(lock_key)
        if record:
            record = record.decode('utf-8')
            return record
        else:
            return None

    async def clear_all(self):
        lock_key = 'RLOCK'
        await self.__srv_redis.mdele_by_prefix(lock_key)
