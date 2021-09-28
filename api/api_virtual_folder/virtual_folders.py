from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv

import requests
from datetime import datetime, timezone

from config import ConfigClass
from models.base_models import APIResponse, PaginationRequest, EAPIResponseCode
from models import virtual_folder_models as models
from resources.dependency import check_folder_permissions
from resources.helpers import fetch_geid
import copy

router = APIRouter()

@cbv(router)
class VirtualFolder:
    @router.get('/', response_model=models.VirtualFolderGETResponse, summary="Get the collection belonging to user")
    async def get(self, project_geid: str, username: str):
        api_response = APIResponse() 
        container_id = self.get_container_id(project_geid)
        if container_id is None:
            api_response.code = EAPIResponseCode.not_found
            api_response.error_msg = "Project not found"
            return api_response.json_response()

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
                "container_id": container_id
            },
        }
        result = requests.post(url, json=payload)
        if result.status_code != 200:
            api_response.code = result.status_code
            api_response.error_msg = "Get folder error"
            return api_response.json_response()
        result = result.json()
        folders = []
        for relation in result:
            node = relation["end_node"]
            folders.append({
                "global_entity_id": node["global_entity_id"],
                "labels": node["labels"],
                "properties": {
                    "name": node["name"],
                    "time_created": node["time_created"],
                    "time_lastmodified": node["time_lastmodified"],
                    "project_geid": node["global_entity_id"],
                }
            })
        api_response.result = folders
        return api_response.json_response()

    @router.post('/', response_model=models.VirtualFolderPOSTResponse, summary="Create a collection")
    async def post(self, data: models.VirtualFolderPOST):
        api_response = models.VirtualFolderPOSTResponse()
        folder_name = data.name
        project_geid = data.project_geid
        username = data.username
        #add internal func
        container_id = self.get_container_id(project_geid)
        if container_id is None:
            api_response.code = EAPIResponseCode.not_found
            api_response.error_msg = "Project not found"
            return api_response.json_response()

        try:
            payload = {
                "username": username
            }
            response = requests.post(ConfigClass.NEO4J_SERVICE + "nodes/User/query", json=payload)
            if not response.json():
                api_response.code = EAPIResponseCode.not_found
                api_response.error_msg = "User not found"
                return api_response.json_response()
            user_node = response.json()[0]
        except Exception as e:
            api_response.code = EAPIResponseCode.internal_error
            api_response.error_msg = f"Neo4j error: {str(e)}"
            return api_response.json_response()
        
        # Folder count check
        url = ConfigClass.NEO4J_SERVICE + 'relations/query'
        payload = {
            "start_label": "User",
            "end_label": "VirtualFolder",
            "start_params": {
                "username": username
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
                "username": username
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
        vfolder_result = result.json()[0]
        vfolder = copy.deepcopy(vfolder_result)
        api_response.result = vfolder

        # Add relation to user
        url = ConfigClass.NEO4J_SERVICE + "relations/owner"
        payload = {
            "start_id": user_node["id"],
            "end_id": vfolder["id"],
        }
        result = requests.post(url, json=payload)
        if result.status_code != 200:
            api_response.error_msg = "Add relation to user Error:" + result.json()
            api_response.code = EAPIResponseCode.internal_error
            return api_response.json_response()
        del vfolder["id"]
        del vfolder["container_id"]
        vfolder["project_geid"] = project_geid
        return api_response.json_response()

    @router.put('/', response_model=models.VirtualFolderPUTResponse, summary="Bulk update virtual folders")
    async def put(self, data: models.VirtualFolderPUT):
        api_response = models.VirtualFolderPOSTResponse()
        username = data.username
        results = []
        update_name = set()
        for collection in data.collections:
            # check required attributes
            for attr in ["name", "geid"]:
                if not collection.get(attr):
                    api_response.error_msg = f"Missing required attribute {attr}"
                    api_response.code = EAPIResponseCode.bad_request
                    return api_response.json_response()
            update_name.add(collection["name"])
        # Check duplicate name in payload
        if len(update_name) != len(data.collections):
            api_response.error_msg = "Duplicate update collection names"
            api_response.code = EAPIResponseCode.bad_request
            return api_response.json_response()

        for vfolder in data.collections:
            # Check folder belongs to user
            url = ConfigClass.NEO4J_SERVICE + f"relations/query"
            payload = {
                "start_label": "User",
                "end_label": "VirtualFolder",
                "start_params": {
                    "username": username,
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
            container_id = vfolder_node["container_id"]

            # duplicate check
            url = ConfigClass.NEO4J_SERVICE + 'relations/query'
            payload = {
                "start_label": "User",
                "end_label": "VirtualFolder",
                "start_params": {
                    "username": username
                },
                "end_params": {
                    "container_id": container_id,
                    "name": vfolder["name"]
                },
            }
            result = requests.post(url, json=payload)
            result = result.json()
            if len(result) > 0:
                api_response.error_msg = "Found duplicate folder"
                api_response.code = EAPIResponseCode.conflict
                return api_response.json_response()

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

            # get container
            url = ConfigClass.NEO4J_SERVICE + f"nodes/Container/node/{container_id}"
            result = requests.get(url)
            if result.status_code != 200:
                api_response.error_msg = "Neo4j Error: " + result.json()
                api_response.code = EAPIResponseCode.internal_error
                return api_response.json_response()
            project_geid = result.json()[0]["global_entity_id"]

            del vfolder["id"]
            del vfolder["container_id"]
            vfolder["project_geid"] = project_geid
            results.append(vfolder)
        api_response.result = results
        return api_response.json_response()
    
    def get_container_id(self, project_geid):
        url = ConfigClass.NEO4J_SERVICE + f"nodes/Container/query"
        payload = {
            "global_entity_id": project_geid
        }
        result = requests.post(url, json = payload)
        if result.status_code != 200 or result.json() == []:
            return None
        result = result.json()[0]
        container_id = result["id"]
        return container_id
