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

import httpx
from fastapi import APIRouter
from fastapi_utils.cbv import cbv
from logger import LoggerFactory

from config import ConfigClass
from models import filemeta_models as models
from models.base_models import EAPIResponseCode
from resources.cataloguing_manager import CataLoguingManager
from resources.error_handler import catch_internal
from resources.helpers import fetch_geid
from fastapi.concurrency import run_in_threadpool

router = APIRouter()


@cbv(router)
class FiledataMeta:
    def __init__(self):
        self._logger = LoggerFactory('api_file_meta').get_logger()

    @router.post('/', response_model=models.FiledataMetaPOSTResponse, summary="Create or Update filedata meta")
    @catch_internal('api_file_meta')
    async def post(self, data: models.FiledataMetaPOST):
        api_response = models.FiledataMetaPOSTResponse()
        self._logger.info("Metadata request receieved")
        cata_mgr = CataLoguingManager()

        # fetch global entity id
        geid = ''
        try:
            geid = await run_in_threadpool(fetch_geid)
        except Exception as e:
            self._logger.error(str(e))
            api_response.result = {'Error when fetching geid'}
            api_response.code = EAPIResponseCode.internal_error
            api_response.error_msg = 'Error when fetching geid'
            return api_response.json_response()

        # create atlas entity
        res_cata = await cata_mgr.create_file_meta(data, geid)

        guid = res_cata['guid']
        self._logger.info(f"Request Data:{data}")

        json_data = {
            "uploader": data.uploader,
            "full_path": data.path + "/" + data.file_name,
            "file_size": data.file_size,
            "description": data.description,
            "namespace": data.namespace,
            "dcm_id": data.dcm_id,
            "guid": guid,
            "tags": data.labels,
            "global_entity_id": geid,
            "project_code": data.project_code,
            "parent_folder_geid": data.parent_folder_geid,
            "operator": data.operator,
            "process_pipeline": data.process_pipeline,
            # minio attribute
            "location": "minio://%s/%s/%s" % (ConfigClass.MINIO_SERVICE, data.bucket, data.minio_object_path),
            "display_path": data.minio_object_path,
            "version_id": data.version_id
        }
        parent_query = data.parent_query
        self._logger.info(
            f"parent_query:{parent_query}, type: {type(parent_query)}")
        if "original_geid" in parent_query:
            json_data["original_geid"] = parent_query["original_geid"]
        self._logger.info(f"Create file data:{json_data}")
        # Get dataset id
        dataset_data = {
            "code": data.project_code,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                ConfigClass.NEO4J_SERVICE + "nodes/Container/query",
                json=dataset_data,
                timeout=None
            )
        if response.status_code != 200:
            error_msg = "Get dataset id:" + str(response.__dict__)
            self._logger.error(error_msg)
            api_response.error_msg = error_msg
            api_response.code = EAPIResponseCode.internal_error
            return api_response.json_response()
        json_data["project_id"] = response.json()[0]["id"]

        self._logger.info("Create the in atlas")

        # Create the file entity
        async with httpx.AsyncClient() as client:
            response = await client.post(
                ConfigClass.ENTITYINFO_SERVICE + "files/",
                json=json_data,
                timeout=None
            )
        if response.status_code != 200:
            error_msg = "Create the file entity error:" + str(response.__dict__)
            self._logger.error(error_msg)
            api_response.error_msg = error_msg
            api_response.code = EAPIResponseCode.internal_error
            return api_response.json_response()
        node = response.json()['result']
        self._logger.info(guid)
        self._logger.info(data.parent_query)

        if data.parent_query:
            parent_query_post_form = {
            }
            if data.parent_query.get("full_path"):
                parent_query_post_form["full_path"] = data.parent_query.get("full_path")
            if data.parent_query.get("geid"):
                parent_query_post_form["global_entity_id"] = data.parent_query.get("geid")
            if data.parent_query.get("global_entity_id"):
                parent_query_post_form["global_entity_id"] = data.parent_query.get("global_entity_id")
            # Get parent file
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    ConfigClass.NEO4J_SERVICE+"nodes/File/query",
                    json=parent_query_post_form,
                    timeout=None
                )
            self._logger.info(response.json())
            input_file_id = response.json()[0]["id"]

            # Create relationship from input to processed
            relation_data = {
                "start_id": input_file_id,
                "end_id": node["id"],
                "properties": {"operator": data.operator}
            }
            pipeline_name = data.process_pipeline
            self._logger.info(relation_data)
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    ConfigClass.NEO4J_SERVICE+f"relations/{data.process_pipeline}",
                    json=relation_data,
                    timeout=None
                )
            self._logger.info(response.json())

        api_response.result = node
        return api_response.json_response()
