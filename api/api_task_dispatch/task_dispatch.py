import requests
import time
import os
from config import ConfigClass
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from models.base_models import EAPIResponseCode, APIResponse
from models import task_dispatch as models
from resources.cataloguing_manager import CataLoguingManager
from resources.helpers import send_message_to_queue
from resources.helpers import fetch_geid
from services.service_logger.logger_factory_service import SrvLoggerFactory
from resources.error_handler import catch_internal
from commons.data_providers.redis_project_session_job import SessionJob, session_job_get_status, session_job_delete_status

router = APIRouter()


@cbv(router)
class TaskDispatcher:
    def __init__(self):
        self._logger = SrvLoggerFactory('api_task_dispatch').get_logger()

    @router.post('/', response_model=models.TaskDispatchPOSTResponse,
                 summary="Asynchronized Task Management API, Create a new task")
    @catch_internal('api_task_dispatch')
    async def post(self, data: models.TaskDispatchPOST):
        api_response = APIResponse()
        session_job = SessionJob(
            data.session_id,
            data.project_code,
            data.action,
            data.operator,
            task_id=data.task_id
        )
        session_job.set_job_id(data.job_id)
        session_job.set_progress(data.progress)
        session_job.set_source(data.source)
        for key in data.payload:
            session_job.add_payload(key, data.payload[key])
        session_job.set_status("INIT")
        session_job.save()
        api_response.code = EAPIResponseCode.success
        api_response.result = "SUCCEED"
        return api_response.json_response()

    @router.get('/', summary="Asynchronized Task Management API, Get task information")
    @catch_internal('api_task_dispatch')
    async def get(self, session_id, job_id="*", project_code="*", action="*", operator="*"):
        api_response = APIResponse()
        fetched = session_job_get_status(
            session_id,
            job_id,
            project_code,
            action,
            operator
        )
        api_response.code = EAPIResponseCode.success
        api_response.result = fetched
        return api_response.json_response()

    @router.delete('/', summary="Asynchronized Task Management API, Delete tasks")
    @catch_internal('api_task_dispatch')
    async def delete(self, data: models.TaskDispatchDELETE):
        api_response = APIResponse()
        fetched = session_job_delete_status(
            data.session_id,
            data.job_id,
            data.project_code,
            data.action,
            data.operator
        )
        api_response.code = EAPIResponseCode.success
        api_response.result = "SUCCEED"
        return api_response.json_response()

    @router.put('/', summary="Asynchronized Task Management API, Update tasks")
    @catch_internal('api_task_dispatch')
    async def put(self, data: models.TaskDispatchPUT):
        api_response = APIResponse()
        my_job = SessionJob(
            data.session_id,
            '*',
            '*',
            '*',
            job_id=data.job_id
        )
        for k, v in data.add_payload.items():
            my_job.add_payload(k, v)
        my_job.set_progress(data.progress)
        my_job.set_status(data.status)
        my_job.save()
        api_response.code = EAPIResponseCode.success
        api_response.result = my_job.to_dict()
        return api_response.json_response()