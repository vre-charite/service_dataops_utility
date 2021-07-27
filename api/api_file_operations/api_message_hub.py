
import requests
import time
import os
from config import ConfigClass
from resources.error_handler import catch_internal
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from models.base_models import EAPIResponseCode, APIResponse
from models import file_ops_models as models
from commons.logger_services.logger_factory_service import SrvLoggerFactory
from commons.data_providers.redis import SrvRedisSingleton

router = APIRouter()


@cbv(router)
class MessageHub:
    def __init__(self):
        self._logger = SrvLoggerFactory('api_message_hub').get_logger()

    @router.post('/', response_model=models.MessageHubPOSTResponse, summary="Used for dev debugging purpose")
    @catch_internal('api_file_operations')
    async def post(self, data: models.MessageHubPOST):
        api_response = APIResponse()
        redis_connector = SrvRedisSingleton()
        self._logger.info("[Message received] " + data.message)
        redis_connector.publish(data.channel, data.message)
        api_response.result = "succeed"
        api_response.code = EAPIResponseCode.success
        return api_response.json_response()
