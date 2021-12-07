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

router = APIRouter()


@cbv(router)
class RLock:
    def __init__(self):
        self._logger = SrvLoggerFactory('api_resource_lock').get_logger()
        self.__mgr = ResourceLockManager()

    async def add_one(self):
        print("wait 1s")
        time.sleep(1)

        return 1

    @router.post('/', response_model=models.RLockResponse,
                 summary="Asynchronized RLock Management API, Create a new RLock")
    @catch_internal('api_resource_lock')
    async def lock(self, data: models.RLockPOST):
        api_response = APIResponse()
        self.__mgr.lock(data.resource_key, data.sub_key)
        api_response.code = EAPIResponseCode.success
        api_response.result = {
            "key": data.resource_key,
            "status": EResourceLockStatus.LOCKED.name
        }
        return api_response.json_response()


    @router.delete('/', response_model=models.RLockResponse,
                 summary="Asynchronized RLock Management API, Remove a RLock")
    @catch_internal('api_resource_lock')
    async def unlock(self, data: models.RLockPOST):
        api_response = APIResponse()
        self.__mgr.unlink(data.resource_key, data.sub_key)
        api_response.code = EAPIResponseCode.success
        api_response.result = {
            "key": data.resource_key,
            "status": EResourceLockStatus.UNLOCKED.name
        }
        return api_response.json_response()


    @router.get('/', response_model=models.RLockResponse,
                summary="Asynchronized RLock Management API, Check a RLock")
    @catch_internal('api_resource_lock')
    async def check_lock(self, resource_key, sub_key='default'):
        api_response = APIResponse()
        result = self.__mgr.check_lock(resource_key, sub_key)
        api_response.code = EAPIResponseCode.success
        api_response.result = {
            "key": resource_key,
            "status": result if result else EResourceLockStatus.UNLOCKED.name
        }
        return api_response.json_response()

    @router.delete('/all', response_model=models.RLockClearResponse,
            summary="Asynchronized RLock Management API, Clear all rlocks")
    @catch_internal('api_resource_lock')
    async def clear_locks(self):
        api_response = APIResponse()
        self.__mgr.clear_all()
        api_response.code = EAPIResponseCode.success
        api_response.result = {
            "key": "all",
            "status": EResourceLockStatus.UNLOCKED.name
        }
        return api_response.json_response()
