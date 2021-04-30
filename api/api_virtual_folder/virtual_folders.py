from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv

import requests
from datetime import datetime, timezone

from config import ConfigClass
from models.base_models import APIResponse, PaginationRequest, EAPIResponseCode
from models import virtual_folder_models as models
from auth import jwt_required 
from resources.dependency import check_folder_permissions
from resources.geid_shortcut import fetch_geid

router = APIRouter()

@cbv(router)
class VirtualFolder:
    current_identity: dict = Depends(jwt_required)

    @router.get('/', response_model=models.VirtualFolderGETResponse, summary="Get folders belonging to user")
    async def get(self, container_id: int):
        api_response = APIResponse() 
        username = self.current_identity["username"]

        # Get folder
        url = ConfigClass.NEO4J_SERVICE + 'relations/query'
        payload = {
            "start_label": "User",
            "end_label": "VirtualFolder",
            "order_by": "time_created",
            "order_type": "ASC",
            "start_params": {
                "name": username
            },
            "end_params": {
                "container_id": int(container_id)
            },
        }
        result = requests.post(url, json=payload)
        if result.status_code != 200:
            api_response.code = result.status_code
            api_response.error_msg = "Get folder error"
        result = result.json()
        folders = []
        for relation in result:
            node = relation["end_node"]
            folders.append({
                "global_entity_id": node["global_entity_id"],
                "identity": node["id"],
                "labels": node["labels"],
                "properties": {
                    "name": node["name"],
                    "time_created": node["time_created"],
                    "time_lastmodified": node["time_lastmodified"],
                    "container_id": node["container_id"],
                }
            })
        api_response.result = folders
        return api_response.json_response()

    @router.post('/', response_model=models.VirtualFolderPOSTResponse, summary="Create a vfolder")
    async def post(self, data: models.VirtualFolderPOST):
        api_response = models.VirtualFolderPOSTResponse()
        folder_name = data.name
        container_id = data.container_id
        username = self.current_identity.get("username")
        user_id = self.current_identity.get("user_id")
        role = self.current_identity.get("role")
        if not username or user_id == None:
            api_response.code = EAPIResponseCode.bad_request
            api_response.error_msg = "Couldn't get user info from jwt token"
            return api_response.json_response()

        if role != "admin":
            # Check user belongs to dataset
            url = ConfigClass.NEO4J_SERVICE + 'relations/query'
            payload = {
                "start_label": "User",
                "end_label": "Dataset",
                "start_params": {
                    "id": int(user_id)
                },
                "end_params": {
                    "id": int(container_id),
                },
            }
            result = requests.post(url, json=payload)
            result = result.json()
            if len(result) < 1:
                api_response.error_msg = "User doesn't belong to project"
                api_response.code = EAPIResponseCode.forbidden
                return api_response.json_response()

        # Folder count check
        url = ConfigClass.NEO4J_SERVICE + 'relations/query'
        payload = {
            "start_label": "User",
            "end_label": "VirtualFolder",
            "start_params": {
                "id": int(user_id)
            },
            "end_params": {
                "container_id": int(container_id),
            },
        }
        result = requests.post(url, json=payload)
        result = result.json()
        if len(result) >= 10:
            api_response.error_msg = "Folder limit reached"
            api_response.code = EAPIResponseCode.bad_request
            return api_response.json_response()

        # duplicate check
        url = ConfigClass.NEO4J_SERVICE + 'relations/query'
        payload = {
            "start_label": "User",
            "end_label": "VirtualFolder",
            "start_params": {
                "id": int(user_id)
            },
            "end_params": {
                "container_id": int(container_id),
                "name": folder_name
            },
        }
        result = requests.post(url, json=payload)
        result = result.json()
        if len(result) > 0:
            api_response.error_msg = "Found duplicate folder"
            api_response.code = EAPIResponseCode.conflict
            return api_response.json_response()

        # Create vfolder in neo4j
        url = ConfigClass.NEO4J_SERVICE + "nodes/VirtualFolder"
        payload = {
            "name": folder_name,
            "container_id": container_id,
            "global_entity_id": fetch_geid(),
        }
        result = requests.post(url, json=payload)
        if result.status_code != 200:
            api_response.error_msg = "Create vfolder in neo4j:" + result.json()
            api_response.code = EAPIResponseCode.internal_error
            return api_response.json_response()
        vfolder = result.json()[0]
        api_response.result = vfolder

        # Add relation to user
        url = ConfigClass.NEO4J_SERVICE + "relations/owner"
        payload = {
            "start_id": user_id,
            "end_id": vfolder["id"],
        }
        result = requests.post(url, json=payload)
        if result.status_code != 200:
            api_response.error_msg = "Add relation to user Error:" + result.json()
            api_response.code = EAPIResponseCode.internal_error
            return api_response.json_response()
        return api_response.json_response()

    @router.put('/', response_model=models.VirtualFolderPUTResponse, summary="Bulk update virtual folders")
    async def put(self, data: models.VirtualFolderPUT):
        api_response = models.VirtualFolderPOSTResponse()
        results = []
        for vfolder in data.vfolders:
            # check required attributes
            for attr in ["name", "geid"]:
                if not vfolder.get(attr):
                    api_response.error_msg = f"Missing required attribute {attr}"
                    api_response.code = EAPIResponseCode.bad_request
                    return api_response.json_response()

            # Check folder belongs to user
            url = ConfigClass.NEO4J_SERVICE + f"relations/query"
            user_id = self.current_identity["user_id"]
            payload = {
                "start_label": "User",
                "end_label": "VirtualFolder",
                "start_params": {
                    "id": int(user_id),
                },
                "end_params": {
                    "global_entity_id": vfolder["geid"],
                },
            }
            result = requests.post(url, json=payload)
            if result.status_code != 200:
                api_response.code = EAPIResponseCode.internal_error
                api_response.error_msg = "Neo4j Error: " + result.json()
                return api_response.json_response()
            result = result.json()
            if len(result) < 1:
                api_response.code = EAPIResponseCode.forbidden
                api_response.error_msg = "Permission Denied"
                return api_response.json_response()

            # Get vfolder by geid
            url = ConfigClass.NEO4J_SERVICE + f"nodes/VirtualFolder/query"
            payload = {
                "global_entity_id": vfolder["geid"],
            }
            result = requests.post(url, json=payload)
            if result.status_code != 200:
                api_response.error_msg = "Neo4j Error: " + result.json()
                api_response.code = EAPIResponseCode.internal_error
                return api_response.json_response()
            vfolder_node = result.json()[0]
            folder_id = vfolder_node["id"]

            # update vfolder in neo4j
            url = ConfigClass.NEO4J_SERVICE + f"nodes/VirtualFolder/node/{folder_id}"
            payload = {
                "name": vfolder["name"],
            }
            result = requests.put(url, json=payload)
            if result.status_code != 200:
                api_response.error_msg = "Neo4j Error: " + result.json()
                api_response.code = EAPIResponseCode.internal_error
                return api_response.json_response()
            vfolder = result.json()[0]
            results.append(vfolder)
        api_response.result = results
        return api_response.json_response()


@cbv(router)
class VirtualFolderFile:
    current_identity: dict = Depends(check_folder_permissions)

    @router.get('/{folder_id}', response_model=models.VirtualFolderFileGETResponse, summary="Get all files in a vfolder")
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

    @router.post('/{folder_id}/files', response_model=models.VirtualFileBulkPOSTResponse, summary="Add files to vfolder")
    def post(self, folder_id, data: models.VirtualFileBulkPOST):
        api_response = models.VirtualFileBulkPOSTResponse()
        geids = data.geids

        # Check folder belongs to user
        url = ConfigClass.NEO4J_SERVICE + f"relations/query"
        user_id = self.current_identity["user_id"]
        payload = {
            "start_label": "User",
            "end_label": "VirtualFolder",
            "start_params": {
                "id": int(user_id),
            },
            "end_params": {
                "id": int(folder_id),
            },
        }
        result = requests.post(url, json=payload)
        if result.status_code != 200:
            api_response.code = EAPIResponseCode.internal_error
            api_response.error_msg = "Check folder belongs to user Error: " + result.json()
            return api_response.json_response()
        result = result.json()
        if len(result) < 1:
            api_response.code = EAPIResponseCode.not_found
            api_response.error_msg = "Folder not found"
            return api_response.json_response()

        vfolder = result[0]["end_node"]

        # Get folders dataset
        url = ConfigClass.NEO4J_SERVICE + f"nodes/Dataset/node/{vfolder['container_id']}"
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
            url = ConfigClass.NEO4J_SERVICE + f"relations/query"
            payload = {
                "start_label": "VirtualFolder",
                "end_label": "File",
                "start_params": {
                    "id": int(folder_id),
                },
                "end_params": {
                    "global_entity_id": geid,
                },
            }
            result = requests.post(url, json=payload)
            if result.status_code != 200:
                api_response.code = EAPIResponseCode.internal_error
                api_response.error_msg = "Duplicate check Error: " + result.json()
                return api_response.json_response()

            if len(result.json()) > 0:
                duplicate = True
                continue

            # Get file from neo4j 
            result = requests.post(ConfigClass.NEO4J_SERVICE + f'nodes/File/query', json={'global_entity_id': geid})
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

            relation_query = {
                "start_id": dataset["id"],
                "end_id": result["id"],
            }
            relation = requests.get(ConfigClass.NEO4J_SERVICE + f'relations', params=relation_query)
            if not relation:
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

    @router.delete('/{folder_id}/files', response_model=models.VirtualFileBulkDELETEResponse, summary="Remove file from folder")
    def delete(self, folder_id, data: models.VirtualFileBulkDELETE):
        api_response = models.VirtualFileBulkDELETEResponse()
        geids = data.geids

        # Check folder belongs to user
        url = ConfigClass.NEO4J_SERVICE + f"relations/query"
        user_id = self.current_identity["user_id"]
        payload = {
            "start_label": "User",
            "end_label": "VirtualFolder",
            "start_params": {
                "id": int(user_id),
            },
            "end_params": {
                "id": int(folder_id),
            },
        }
        result = requests.post(url, json=payload)
        if result.status_code != 200:
            api_response.code = EAPIResponseCode.internal_error
            api_response.error_msg = "Check folder belongs to user Error: " + result.json()
            return api_response.json_response()
        result = result.json()
        if len(result) < 1:
            api_response.code = EAPIResponseCode.forbidden
            api_response.error_msg = "Folder does not belong to user" 
            return api_response.json_response()

        for geid in geids:
            # Get file
            url = ConfigClass.NEO4J_SERVICE + f"relations/query"
            payload = {
                "start_label": "VirtualFolder",
                "end_label": "File",
                "start_params": {
                    "id": int(folder_id),
                },
                "end_params": {
                    "global_entity_id": geid,
                },
            }
            result = requests.post(url, json=payload)
            if result.status_code != 200:
                api_response.code = EAPIResponseCode.internal_error
                api_response.error_msg = "Get file Error: " + result.json()
                return api_response.json_response()
            result = result.json()
            if len(result) > 1:
                api_response.code = EAPIResponseCode.internal_error
                api_response.error_msg = "multiple files, aborting"
                return api_response.json_response()
            file_id = result[0]["end_node"]["id"]
            relation_query = {
                "start_id": int(folder_id),
                "end_id": file_id,
            }
            # Remove relationship from neo4j
            result = requests.delete(ConfigClass.NEO4J_SERVICE + "relations", params=relation_query)
            if result.status_code != 200:
                api_response.code = EAPIResponseCode.internal_error
                api_response.error_msg = "Remove relationship from neo4j Error: " + result.json()
                return api_response.json_response()
        api_response.result = 'success'
        return api_response.json_response()
