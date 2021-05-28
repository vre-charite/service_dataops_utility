from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv

import requests
from datetime import datetime, timezone

from config import ConfigClass
from models.base_models import APIResponse, PaginationRequest, EAPIResponseCode
from models import virtual_folder_models as models
from auth import jwt_required 
from resources.dependency import check_folder_permissions
from resources.helpers import fetch_geid
import copy

router = APIRouter()

@cbv(router)
class VirtualFolderFile:
    current_identity: dict = Depends(check_folder_permissions)

    @router.get('/{folder_id}', response_model=models.VirtualFolderFileGETResponse, summary="Get all files in a vfolder", deprecated=True)
    async def get(self, folder_id, page_params: PaginationRequest = Depends(PaginationRequest)):
        api_response = models.VirtualFolderFileGETResponse()

        # Get file by folder relation
        url = ConfigClass.NEO4J_SERVICE + f"relations/query"
        payload = {
            "start_label": "VirtualFolder",
            "end_label": "File",
            "start_params": {
                "id": int(folder_id),
            },
            "end_params": {
                "archived": False,
            },
            "limit": page_params.page_size,
            "skip": page_params.page * page_params.page_size,
            "order_by": page_params.order_by,
            "order_type": page_params.order_type,
        }
        result = requests.post(url, json=payload)
        if result.status_code != 200:
            api_response.error_msg = "Get file by folder relation error:" + result.json()
            api_response.code = EAPIResponseCode.internal_error
            return api_response.json_response()
        result = result.json()
        if not result:
            # No file found in folder
            api_response.result = []
            return api_response
        results = [i["end_node"] for i in result]
        # Pagination
        total = len(result)
        api_response.total = total
        api_response.page = page_params.page
        api_response.num_of_pages = int(int(total) / int(page_params.page_size))
        api_response.result = results
        return api_response.json_response()


    @router.put('/{folder_id}', response_model=models.VirtualFolderFilePUTResponse, summary="Edit folder name")
    async def put(self, folder_id, data: models.VirtualFolderFilePUT):
        api_response = models.VirtualFolderFilePUTResponse()
        folder_name = data.name
        if not folder_name:
            api_response.error_msg = "Missing required fields"
            api_response.code = EAPIResponseCode.bad_request
            return api_response.json_response()

        # update vfolder in neo4j
        url = ConfigClass.NEO4J_SERVICE + f"nodes/VirtualFolder/node/{folder_id}"
        payload = {
            "name": folder_name,
        }
        result = requests.put(url, json=payload)
        if result.status_code != 200:
            api_response.error_msg = "update vfolder in neo4j Error: " + result.json()
            api_response.code = EAPIResponseCode.internal_error
            return api_response.json_response()
        vfolder = result.json()[0]
        api_response.result = vfolder
        return api_response.json_response()

    @router.delete('/{folder_id}', response_model=models.VirtualFolderFileDELETEResponse, summary="Delete a vfolder")
    async def delete(self, folder_id):
        api_response = models.VirtualFolderFileDELETEResponse()
        url = ConfigClass.NEO4J_SERVICE + f"nodes/VirtualFolder/node/{folder_id}"
        result = requests.delete(url)
        if result.status_code != 200:
            api_response.code = EAPIResponseCode.internal_error
            api_response.error_msg = "VirtualFolderFileDELETEResponse Error: " + result.json()
            return api_response.json_response()
        api_response.result = 'success'
        return api_response.json_response()


@cbv(router)
class FileBulk:
    current_identity: dict = Depends(jwt_required)

    @router.post('/{folder_geid}/files', response_model=models.VirtualFileBulkPOSTResponse, summary="Add files to vfolder")
    def post(self, folder_geid, data: models.VirtualFileBulkPOST):
        api_response = models.VirtualFileBulkPOSTResponse()
        geids = data.geids

        # Get vfolder
        url = ConfigClass.NEO4J_SERVICE + f"nodes/VirtualFolder/query"
        payload = {
            "global_entity_id": folder_geid,
        }
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            api_response.code = response.status_code
            api_response.error_msg = response.json()
            return api_response.json_response()
        vfolder = response.json()[0]

        # Get folders dataset
        container_id = vfolder["container_id"]
        url = ConfigClass.NEO4J_SERVICE + f"nodes/Dataset/node/{container_id}"
        result = requests.get(url)
        if result.status_code != 200:
            api_response.code = EAPIResponseCode.internal_error
            api_response.error_msg = "Get folders dataset Error: " + result.json()
            return api_response.json_response()
        if len(result.json()) < 1:
            api_response.code = EAPIResponseCode.not_found
            api_response.error_msg = "Project not found"
            return api_response.json_response()

        dataset = result.json()[0]

        duplicate = False
        for geid in geids:
            #Duplicate check
            url = ConfigClass.NEO4J_SERVICE_V2 + f"relations/query"
            payload = {
                "start_label": "VirtualFolder",
                "end_labels": ["File", "Folder"],
                "query": {
                    "start_params": {
                        "global_entity_id": vfolder["global_entity_id"],
                    },
                    "end_params": {
                        "File": {
                            "global_entity_id": geid,
                        },
                        "Folder": {
                            "global_entity_id": geid,
                        },
                    },
                }
            }
            result = requests.post(url, json=payload)
            if result.status_code != 200:
                api_response.code = EAPIResponseCode.internal_error
                api_response.error_msg = "Duplicate check Error: " + result.json()
                return api_response.json_response()

            if len(result.json()["results"]) > 0:
                duplicate = True
                continue

            # Get file from neo4j 
            payload = {
                "global_entity_id": geid,
            }
            try:
                result = requests.post(ConfigClass.NEO4J_SERVICE + f'nodes/File/query', json=payload)
                result = result.json()[0]
            except:
                result = requests.post(ConfigClass.NEO4J_SERVICE + f'nodes/Folder/query', json=payload)
                result = result.json()[0]

            if not result:
                api_response.code = EAPIResponseCode.not_found
                api_response.error_msg = "File not found in neo4j"
                return api_response.json_response()

            # Check to make sure it's a VRE core file
            if not "VRECore" in result["labels"]:
                api_response.code = EAPIResponseCode.forbidden
                api_response.error_msg = "Permission denied"
                return api_response.json_response()

            if result["project_code"] != dataset["code"]:
                api_response.code = EAPIResponseCode.forbidden
                api_response.error_msg = "File does not belong to project"
                return api_response.json_response()

            # Add folder relation to file
            url = ConfigClass.NEO4J_SERVICE + f"relations/contains"
            payload = {
                "start_id": vfolder["id"],
                "end_id": result["id"],
            }
            result = requests.post(url, json=payload)
            if result.status_code != 200:
                api_response.code = EAPIResponseCode.internal_error
                api_response.error_msg = "Add folder relation to file Error: " + result.json()
                return api_response.json_response()

        if duplicate:
            api_response.result = "duplicate"
        else:
            api_response.result = "success"
        return api_response.json_response()

    @router.delete('/{folder_geid}/files', response_model=models.VirtualFileBulkDELETEResponse, summary="Remove file from folder")
    def delete(self, folder_geid, data: models.VirtualFileBulkDELETE):
        api_response = models.VirtualFileBulkDELETEResponse()
        geids = data.geids

        for geid in geids:
            # Get vfolder
            url = ConfigClass.NEO4J_SERVICE + f"nodes/VirtualFolder/query"
            payload = {
                "global_entity_id": folder_geid,
            }
            response = requests.post(url, json=payload)
            if response.status_code != 200:
                api_response.code = response.status_code
                api_response.error_msg = response.json()
                return api_response.json_response()
            if not response.json():
                api_response.code = EAPIResponseCode.not_found
                api_response.error_msg = "Virtual Folder not found"
                return api_response.json_response()
            folder_id = response.json()[0]["id"]

            # Get file
            url = ConfigClass.NEO4J_SERVICE_V2 + f"relations/query"
            payload = {
                "start_label": "VirtualFolder",
                "end_labels": ["File", "Folder"],
                "query": {
                    "start_params": {
                        "global_entity_id": folder_geid,
                    },
                    "end_params": {
                        "File": {
                            "global_entity_id": geid,
                        },
                        "Folder": {
                            "global_entity_id": geid,
                        }
                    },
                }
            }
            result = requests.post(url, json=payload)
            if result.status_code != 200:
                api_response.code = EAPIResponseCode.internal_error
                api_response.error_msg = "Get file Error: " + result.json()
                return api_response.json_response()
            result = result.json()["results"]
            if len(result) > 1:
                api_response.code = EAPIResponseCode.internal_error
                api_response.error_msg = "multiple files, aborting"
                return api_response.json_response()
            if not result:
                api_response.code = EAPIResponseCode.not_found
                api_response.error_msg = "File not found"
                return api_response.json_response()
            file_id = result[0]["id"]

            # Remove relationship from neo4j
            relation_query = {
                "start_id": int(folder_id),
                "end_id": file_id,
            }
            result = requests.delete(ConfigClass.NEO4J_SERVICE + "relations", params=relation_query)
            if result.status_code != 200:
                api_response.code = EAPIResponseCode.internal_error
                api_response.error_msg = "Remove relationship from neo4j Error: " + result.json()
                return api_response.json_response()
        api_response.result = 'success'
        return api_response.json_response()
