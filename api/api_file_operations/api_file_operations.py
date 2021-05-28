import requests
import time
import os
from config import ConfigClass
from resources.error_handler import catch_internal
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from models.base_models import EAPIResponseCode, APIResponse
from models import file_ops_models as models
from resources.cataloguing_manager import CataLoguingManager
from commons.logger_services.logger_factory_service import SrvLoggerFactory
from .copy_dispatcher import copy_dispatcher
from .delete_dispatcher import delete_dispatcher

router = APIRouter()


@cbv(router)
class FileOperations:
    def __init__(self):
        self._logger = SrvLoggerFactory('api_file_operations').get_logger()

    @router.post('/', response_model=models.FileOperationsPOSTResponse, summary="File operations api, invoke an async file operation job")
    @catch_internal('api_file_operations')
    async def post(self, data: models.FileOperationsPOST):
        api_response = APIResponse()
        # permission control, operation lock
        # selete operation worker
        job_dispatcher = {
            "copy": copy_dispatcher,
            "delete": delete_dispatcher
        }.get(data.operation, None)
        if not job_dispatcher:
            api_response.code = EAPIResponseCode.bad_request
            api_response.error_msg = "Invalid operation"
            return api_response.json_response()
        code, result = job_dispatcher(self._logger, data)
        api_response.code = code
        if not api_response.code == EAPIResponseCode.accepted:
            api_response.error_msg = "Error occured"
        api_response.result = result
        return api_response.json_response()
