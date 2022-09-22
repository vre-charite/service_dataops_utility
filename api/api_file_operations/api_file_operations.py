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

from typing import Optional

from fastapi import APIRouter
from fastapi import Header
from fastapi_utils.cbv import cbv
from logger import LoggerFactory

from api.api_file_operations.copy_dispatcher import CopyDispatcher
from api.api_file_operations.delete_dispatcher import DeleteDispatcher
from models import file_ops_models as models
from models.base_models import APIResponse
from models.base_models import EAPIResponseCode
from resources.error_handler import catch_internal

router = APIRouter()


@cbv(router)
class FileOperations:
    def __init__(self):
        self._logger = LoggerFactory('api_file_operations').get_logger()

    @router.post(
        '/',
        response_model=models.FileOperationsPOSTResponse,
        summary='File operations api, invoke an async file operation job',
    )
    @catch_internal('api_file_operations')
    async def post(
        self,
        data: models.FileOperationsPOST,
        authorization: Optional[str] = Header(None),
        refresh_token: Optional[str] = Header(None),
    ):
        token = {
            'at': authorization,
            'rt': refresh_token,
        }

        self._logger.info(f'Request tokens: {token}.')

        job_dispatcher = {
            'copy': CopyDispatcher,
            'delete': DeleteDispatcher,
        }.get(data.operation, None)

        api_response = APIResponse()

        if not job_dispatcher:
            api_response.code = EAPIResponseCode.bad_request
            api_response.error_msg = 'Invalid operation'
            return api_response.json_response()

        code, result = await job_dispatcher().execute(self._logger, data, token)
        api_response.code = code
        if not api_response.code == EAPIResponseCode.accepted:
            api_response.error_msg = 'Error occurred'
        api_response.result = result

        return api_response.json_response()
