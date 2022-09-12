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

from fastapi import APIRouter
from fastapi_utils.cbv import cbv
from logger import LoggerFactory

from resources.redis import SrvAioRedisSingleton
from models import file_ops_models as models
from models.base_models import APIResponse
from models.base_models import EAPIResponseCode
from resources.error_handler import catch_internal

router = APIRouter()


@cbv(router)
class MessageHub:
    def __init__(self):
        self._logger = LoggerFactory('api_message_hub').get_logger()

    @router.post('/', response_model=models.MessageHubPOSTResponse, summary="Used for dev debugging purpose")
    @catch_internal('api_file_operations')
    async def post(self, data: models.MessageHubPOST):
        api_response = APIResponse()
        redis_connector = SrvAioRedisSingleton()
        self._logger.info("[Message received] " + data.message)
        await redis_connector.publish(data.channel, data.message)
        api_response.result = "succeed"
        api_response.code = EAPIResponseCode.success
        return api_response.json_response()
