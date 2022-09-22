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

from typing import List
from typing import Tuple

from fastapi import APIRouter
from fastapi import Depends
from fastapi.responses import JSONResponse
from fastapi_utils.cbv import cbv
from logger import LoggerFactory
from pydantic import BaseModel

from dependencies import Cache
from dependencies import get_cache
from models.base_models import EAPIResponseCode
from models.resource_lock_reqres import ResourceLockBulkRequestBody
from models.resource_lock_reqres import ResourceLockBulkResponse
from models.resource_lock_reqres import ResourceLockRequestBody
from models.resource_lock_reqres import ResourceLockResponse
from models.resource_lock_reqres import ResourceLockResponseResult
from resources.error_handler import catch_internal

logger = LoggerFactory('api_resource_lock').get_logger()

router = APIRouter()


class BulkLockResult(BaseModel):
    status: List[Tuple[str, bool]]

    def is_successful(self) -> bool:
        """Return true if all statuses are true."""

        return all(status for _, status in self.status)


class ResourceLocker:
    def __init__(self, cache: Cache = Depends(get_cache)) -> None:
        self._cache = cache

    def str_to_int_list(self, input_: bytes) -> List[int]:
        return [int(x) for x in input_.decode('utf-8').split(',')]

    def int_list_to_str(self, input_: [int]) -> str:
        return ','.join([str(x) for x in input_])

    async def perform_bulk_lock(self, keys: List[str], operation: str) -> BulkLockResult:
        """Perform bulk lock for multiple keys.

        If one of the lock attempts fails, the locking attempts of the following keys are stopped.
        """

        keys = sorted(keys)
        status = []
        have_failed_lock = False

        for key in keys:
            if have_failed_lock:
                status.append((key, False))
                continue

            is_successful = await self.perform_rw_lock(key, operation)
            status.append((key, is_successful))

            if not is_successful:
                have_failed_lock = True

        return BulkLockResult(status=status)

    async def perform_bulk_unlock(self, keys: List[str], operation: str) -> BulkLockResult:
        """Perform bulk unlock for multiple keys."""

        keys = sorted(keys)
        status = []

        for key in keys:
            is_successful = await self.perform_rw_unlock(key, operation)
            status.append((key, is_successful))

        return BulkLockResult(status=status)

    async def perform_rw_lock(self, key: str, operation: str) -> bool:
        """
        Description:
            An async function will do the read/write lock on the key.
            Inside Redis, the entry will be key:"<read_count>, <write_count>"(no bracket)
            read_count will be >=0, while write_count CAN ONLY be 0 or 1.
            ----
            The read count will increase one, if there is a new read operation
            (eg. download). Once the operation finish, the count will decrease one.
            During the read operation, other read operation will proceed as well.
            But write operation is not allowed.
            ---
            The write will increase one, if there a write operation(eg.delete). And
            any other operation will be blocked.
            ---
            Therefore, the value pairs will be (N, 0), (0, 1). Also to avoid the racing
            condition, the await keyword will be used for the function.
        Parameters:
            - key: the object path in minio (eg. <bucket>/file.py)
            - operation: either read or write
        Return:
            - True: the lock operation is success
            - False: the other operation blocks the current one
        """

        if await self._cache.is_exist(key):
            rw_str = await self._cache.get(key)
            # index 0 is read_count, index 1 is write_count
            read_count, write_count = tuple(self.str_to_int_list(rw_str))
            logger.info(f'Found key:{key}, with r/w {read_count}/{write_count}')

            # read_count > 0 -> block write
            if read_count > 0 and operation == 'write':
                return False
            # write_count > 0 -> block all
            elif write_count > 0:
                return False

        # TODO might refactor here later
        if operation == 'read':
            # check if the key exist, if not exist then create pair with (1,0)
            # else increase the read count(index 0) by one
            if await self._cache.is_exist(key):
                rw_str = await self._cache.get(key)
                read_count, write_count = tuple(self.str_to_int_list(rw_str))
                await self._cache.set(key, self.int_list_to_str([read_count + 1, write_count]))
            else:
                await self._cache.set(key, '1,0')

        else:
            await self._cache.set(key, '0,1')

        logger.info(f'Add {operation} lock to {key}')

        return True

    async def perform_rw_unlock(self, key: str, operation: str) -> bool:
        """
        Description:
            An async function to reduce the read_write count based on key.
            ---
            Read count can be "N,0", so each operation will do N-1. if count is
            "1,0" then function will remove the entry for cleanup
            ---
            Write count can only be "0,1", so function will just remove it. BUT
            to check the validation, the pair must be "0,1". Otherwise, we might
            remove the read count by accident.
            ---
            Also to avoid the racing issue, we use the awwait
        Parameters:
            - key: the object path in minio (eg. <bucket>/file.py)
            - operation: either read or write
        Return:
            - True: the lock operation is success
            - False: the other operation blocks the current one
        """

        # we cannot unlock the IDLE file
        if not await self._cache.is_exist(key):
            return False

        # TODO: might need some check here
        # delete cannot just remove the entry
        rw_str = await self._cache.get(key)
        read_count, write_count = tuple(self.str_to_int_list(rw_str))
        logger.info(f'Found key:{key}, with r/w {read_count}/{write_count}')
        if operation == 'read':
            # if the current read operation is the last one
            # then we just remove the entry for cleanup
            if read_count > 1:
                await self._cache.set(key, self.int_list_to_str([read_count - 1, write_count]))
            else:
                await self._cache.delete(key)

        else:
            # corner case if there are some read operation ongoing(readcount>0)
            # we should block the delete on the key
            if read_count > 0:
                return False
            else:
                await self._cache.delete(key)

        logger.info(f'Remove {operation} lock to {key}')

        return True


@cbv(router)
class RLock:
    @router.post('/', response_model=ResourceLockResponse, summary='Create a new lock')
    @catch_internal('api_resource_lock')
    async def lock(self, data: ResourceLockRequestBody, resource_locker: ResourceLocker = Depends()) -> JSONResponse:
        unlocked = await resource_locker.perform_rw_lock(data.resource_key, data.operation)

        api_response = ResourceLockResponse(
            code=EAPIResponseCode.success if unlocked else EAPIResponseCode.conflict,
            result=ResourceLockResponseResult(key=data.resource_key),
        )

        return api_response.json_response()

    @router.post('/bulk', response_model=ResourceLockBulkResponse, summary='Create multiple locks')
    @catch_internal('api_resource_lock')
    async def bulk_lock(
        self, body: ResourceLockBulkRequestBody, resource_locker: ResourceLocker = Depends()
    ) -> JSONResponse:
        lock_result = await resource_locker.perform_bulk_lock(body.resource_keys, body.operation)

        api_response = ResourceLockBulkResponse(
            code=EAPIResponseCode.success if lock_result.is_successful() else EAPIResponseCode.conflict,
            result=lock_result.status,
        )

        return api_response.json_response()

    @router.delete('/', response_model=ResourceLockResponse, summary='Remove a lock')
    @catch_internal('api_resource_lock')
    async def unlock(self, data: ResourceLockRequestBody, resource_locker: ResourceLocker = Depends()) -> JSONResponse:
        flag = await resource_locker.perform_rw_unlock(data.resource_key, data.operation)

        api_response = ResourceLockResponse(
            code=EAPIResponseCode.success if flag else EAPIResponseCode.bad_request,
            result=ResourceLockResponseResult(key=data.resource_key),
        )

        return api_response.json_response()

    @router.delete('/bulk', response_model=ResourceLockBulkResponse, summary='Remove multiple locks')
    @catch_internal('api_resource_lock')
    async def bulk_unlock(
        self, body: ResourceLockBulkRequestBody, resource_locker: ResourceLocker = Depends()
    ) -> JSONResponse:
        lock_result = await resource_locker.perform_bulk_unlock(body.resource_keys, body.operation)

        api_response = ResourceLockBulkResponse(
            code=EAPIResponseCode.success if lock_result.is_successful() else EAPIResponseCode.bad_request,
            result=lock_result.status,
        )

        return api_response.json_response()

    @router.get('/', response_model=ResourceLockResponse, summary='Check a lock')
    @catch_internal('api_resource_lock')
    async def check_lock(self, resource_key: str, cache: Cache = Depends(get_cache)) -> JSONResponse:
        result = await cache.get(resource_key)
        if result is not None:
            result = result.decode()

        api_response = ResourceLockResponse(
            code=EAPIResponseCode.success,
            result=ResourceLockResponseResult(key=resource_key, status=result),
        )

        return api_response.json_response()
