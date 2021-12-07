from typing import Union
import requests
import time
import os
from config import ConfigClass
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from models.base_models import EAPIResponseCode, APIResponse
from models import resource_lock_reqres as models
from resources.helpers import fetch_geid
from services.service_logger.logger_factory_service import SrvLoggerFactory
from resources.error_handler import catch_internal
from models.resource_lock_mgr import ResourceLockManager, EResourceLockStatus

from commons.data_providers.redis import SrvRedisSingleton

router = APIRouter()

# TODO make into util or helper
# or  return the read_count or write count
def str_2_intlist(input:bytes) -> [int]:
    return [int(x) for x in input.decode("utf-8").split(",")]
def intlist_2_str(input:[int]) -> str:
    return ",".join([str(x) for x in input])




@cbv(router)
class RLock:
    def __init__(self):
        self._logger = SrvLoggerFactory('api_resource_lock').get_logger()
        self._redis_client = SrvRedisSingleton()

    async def perform_rw_lock(self, key:str, operation:str) -> bool:
        '''
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
            condition, the await keyword will be used for the function. For more info
            Please check VRE-2102
        Parameters:
            - key: the object path in minio (eg. <bucket>/file.py)
            - operation: either read or write
        Return:
            - True: the lock operation is success
            - False: the other operation blocks the current one
        '''

        # do the lock check
        # TODO decorator?????
        if self._redis_client.check_by_key(key):
            rw_str = self._redis_client.get_by_key(key)
            # index 0 is read_count, index 1 is write_count
            read_count, write_count = tuple(str_2_intlist(rw_str))
            self._logger.info("found key:%s, with r/w %d/%d"%(key, read_count, write_count))

            # read_count > 0 -> block write
            if read_count > 0 and operation == "write":
                return False
            # write_count > 0 -> block all
            elif write_count > 0:
                return False

        # TODO might refactor here later
        if operation == 'read':
            # check if the key exist, if not exist then create pair with (1,0)
            # else increase the read count(index 0) by one
            if self._redis_client.check_by_key(key):
                rw_str = self._redis_client.get_by_key(key)
                read_count, write_count = tuple(str_2_intlist(rw_str))
                self._redis_client.set_by_key(key, intlist_2_str([read_count+1, write_count]))
            else:
                self._redis_client.set_by_key(key, "1,0")

        else:
            self._redis_client.set_by_key(key, "0,1")

        self._logger.info("Add %s lock to %s"%(operation, key))
        

        return True

    async def perform_rw_unlock(self, key:str, operation:str) -> bool:

        '''
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
        '''


        # we cannot unlock the IDLE file
        if not self._redis_client.check_by_key(key):
            return False

        # TODO: might need some check here
        # delete cannot just remove the entry 
        rw_str = self._redis_client.get_by_key(key)
        read_count, write_count = tuple(str_2_intlist(rw_str))
        self._logger.info("found key:%s, with r/w %d/%d"%(key, read_count, write_count))
        if operation == "read":
            # if the current read operation is the last one
            # then we just remove the entry for cleanup
            if read_count > 1:
                self._redis_client.set_by_key(key, intlist_2_str([read_count-1, write_count]))
            else:
                self._redis_client.delete_by_key(key)
            
        else:
            # corner case if there are some read operation ongoing(readcount>0)
            # we should block the delete on the key
            if read_count > 0: return False
            else: self._redis_client.delete_by_key(key)

        # time.sleep(5)
        self._logger.info("Remove %s lock to %s"%(operation, key))

        return True


    @router.post('/', response_model=models.RLockResponse,
                 summary="Asynchronized RLock Management API, Create a new RLock")
    @catch_internal('api_resource_lock')
    async def lock(self, data:models.FileLock):
        api_response = APIResponse()

        # self.__mgr.lock(data.resource_key, data.sub_key)
        unlocked = await self.perform_rw_lock(data.resource_key, data.operation)

        api_response.code = EAPIResponseCode.success if unlocked else EAPIResponseCode.conflict
        api_response.result = {
            "key": data.resource_key,
        }
        return api_response.json_response()


    @router.delete('/', response_model=models.RLockResponse,
                 summary="Asynchronized RLock Management API, Remove a RLock")
    @catch_internal('api_resource_lock')
    async def unlock(self, data: models.FileLock):
        api_response = APIResponse()

        flag = await self.perform_rw_unlock(data.resource_key, data.operation)

        api_response.code = EAPIResponseCode.success if flag else EAPIResponseCode.bad_request
        api_response.result = {
            "key": data.resource_key,
        }
        return api_response.json_response()


    @router.get('/', response_model=models.RLockResponse,
                summary="Asynchronized RLock Management API, Check a RLock")
    @catch_internal('api_resource_lock')
    async def check_lock(self, resource_key):
        '''
        for test ONLY
        '''

        api_response = APIResponse()

        result = self._redis_client.get_by_key(resource_key)
        
        api_response.code = EAPIResponseCode.success
        api_response.result = {
            "key": resource_key,
            # return None if there is no value, else return the count
            "status": str(result) if result else None
        }
        return api_response.json_response()
