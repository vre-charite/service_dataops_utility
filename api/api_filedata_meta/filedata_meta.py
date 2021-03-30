from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from models import filemeta_models as models
from models import file_deletion_models as deletion_models
from models.base_models import EAPIResponseCode
from resources.cataloguing_manager import CataLoguingManager
from resources.message_sender import send_message_to_queue
from resources.geid_shortcut import fetch_geid
from services.service_logger.logger_factory_service import SrvLoggerFactory
from config import ConfigClass
import os
import time
import requests

import requests

router = APIRouter()

@cbv(router)
class FiledataMeta:
    def __init__(self):
        self._logger = SrvLoggerFactory('api_file_meta').get_logger()

    @router.post('/', response_model=models.FiledataMetaPOSTResponse, summary="Create or Update filedata meta")
    async def post(self, data: models.FiledataMetaPOST):
        api_response = models.FiledataMetaPOSTResponse() 
        self._logger.info("Metadata request receieved")
        cata_mgr = CataLoguingManager()

        # fetch global entity id
        geid = ''
        try:
            geid = fetch_geid('file_data')
        except Exception as e:
            self._logger.error(str(e))
            api_response.result = {'Error when fetching geid'}
            api_response.code = EAPIResponseCode.internal_error
            api_response.error_msg = 'Error when fetching geid'
            return api_response.json_response()

        # create atlas entity
        res_cata = cata_mgr.create_file_meta(data, geid)

        guid = res_cata['guid']
        self._logger.info(f"Request Data:{data}")

        json_data = {
            "uploader": data.uploader,
            "full_path": data.path + "/" + data.file_name,
            "file_size": data.file_size,
            "description": data.description,
            "namespace": data.namespace,
            "type": data.data_type,
            "generate_id": data.generate_id,
            "guid": guid,
            "tags": data.labels,
            "global_entity_id": geid,
            "project_code": data.project_code,
            "parent_folder_geid": data.parent_folder_geid,
        }
        if data.data_type == "processed":
            json_data["operator"] = data.operator
            json_data["process_pipeline"] = data.process_pipeline

        # Get dataset id
        dataset_data = {
            "code": data.project_code,
        }
        response = requests.post(ConfigClass.NEO4J_HOST + "/v1/neo4j/nodes/Dataset/query", json=dataset_data)
        if response.status_code != 200:
            api_response.error_msg = "Neo4j error:" + str(response.json())
            api_response.code = EAPIResponseCode.internal_error
            return api_response.json_response()
        json_data["project_id"] = response.json()[0]["id"]

        # Create the file entity
        response = requests.post(ConfigClass.FILEINFO_HOST+ "/v1/files", json=json_data)
        if response.status_code != 200:
            api_response.error_msg = "Neo4j error:" + str(response.json())
            api_response.code = EAPIResponseCode.internal_error
            return api_response.json_response()
        node = response.json()['result']
        self._logger.info(guid)
        self._logger.info(data.parent_query)

        if data.parent_query:
            # Get parent file
            response = requests.post(ConfigClass.NEO4J_HOST + "/v1/neo4j/nodes/File/query", json=data.parent_query)
            self._logger.info(response.json())
            input_file_id = response.json()[0]["id"]

            # Create relationship from input to processed
            relation_data = {
                "start_id": input_file_id,
                "end_id": node["id"],
            }
            pipeline_name = data.process_pipeline
            self._logger.info(relation_data)
            response = requests.post(ConfigClass.NEO4J_HOST + f"/v1/neo4j/relations/{data.process_pipeline}", json=relation_data)
            self._logger.info(response.json())

        api_response.result = node
        return api_response.json_response()

    @router.delete('/', response_model=deletion_models.FiledataDeletionPOSTResponse, summary="Archive filedata")
    async def delete(self, data: deletion_models.FiledataDeletionPOST):
        api_response = deletion_models.FiledataDeletionPOSTResponse()

        for record in data.to_delete:
            try:
                # Get disk path
                namespace = record['namespace']
                disk_path = {
                    "greenroom": ConfigClass.NFS_ROOT_PATH,
                    "vrecore": ConfigClass.VRE_ROOT_PATH
                }.get(namespace, None)

                if not disk_path:
                    api_response.code = EAPIResponseCode.bad_request
                    api_response.error_msg = "Invalid namespace: " + data.namespace
                    return api_response.json_response()

                input_path = record['path'] + "/" + record['file_name']

                # Check if path valid to be deleted
                check_url = ConfigClass.DATA_OPS_GR + "/v1/file-exists"
                check_result = requests.post(url=check_url, json={"full_path": input_path})
                check_res_bool = check_result.json()["result"]

                if not check_res_bool:
                    api_response.code = EAPIResponseCode.bad_request
                    api_response.error_msg = "Invalid input path, file does not exist: " + input_path
                    return api_response.json_response()

                # Get new filename
                file_name_split = os.path.splitext(record['file_name'])
                new_file_name = file_name_split[0] + '_' + str(round(time.time())) + file_name_split[1] \
                    if len(file_name_split) > 0 else file_name_split[0] + '_' + str(round(time.time()))

                # Send message to the queue
                message_payload = {
                    "event_type": "file_delete",
                    "payload": {
                        "session_id": data.session_id,
                        "job_id": data.job_id,
                        "operator": data.operator,
                        "input_path": input_path,
                        "output_path": disk_path  + "/TRASH/" + data.project_code  + "/" + new_file_name,
                        "trash_path": disk_path  + "/TRASH",
                        "generate_id": record.get('generate_id', 'undefined'),
                        "generic": True,
                        "uploader": record.get("uploader", ""),
                        "namespace": namespace,
                        "project": data.project_code,
                    },
                    "create_timestamp": time.time()
                }
                print("Start deleting file: " + str(message_payload))
                res = send_message_to_queue(message_payload)

                # Set status
                status_post_json = {
                    "session_id": data.session_id,
                    "job_id": data.job_id,
                    "source": input_path,
                    "action": "data_delete",
                    "target_status": "running",
                    "project_code": data.project_code,
                    "operator": data.operator
                }
                status_post_res = requests.post(url=ConfigClass.DATA_OPS_GR + "/v1/file/actions/status",
                    json=status_post_json)
            except Exception as e:
                api_response.code = EAPIResponseCode.internal_error
                api_response.result = None
                api_response.error_msg = "Error when sending tasks to the queue: " + str(e)
                print(api_response.error_msg)
                return api_response.json_response()
        api_response.code = EAPIResponseCode.success
        api_response.result = {
            'message': 'Succeed',
        }
        return api_response.json_response()
