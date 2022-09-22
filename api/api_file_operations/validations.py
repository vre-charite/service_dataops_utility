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

from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple
from config import ConfigClass
from models.base_models import EAPIResponseCode
from resources.helpers import http_query_node
import httpx

async def validate_project(project_geid):
    '''
    validate project info, return tulpe(response_code, errormessage/project_info)
    '''
    # validate project
    project_res = await http_query_node(
        "Container", {"global_entity_id": project_geid})
    if project_res.status_code != 200:
        return EAPIResponseCode.internal_error, "Query node error: " + str(project_res.text)
    project_found = project_res.json()
    if len(project_found) == 0:
        return EAPIResponseCode.bad_request, "Invalid project_geid, Project not found: " + project_geid
    project_info = project_found[0]
    return EAPIResponseCode.success, project_info


def validate_operation(target_action, current_action):
    '''
    validate if the operation eligible to be performed, return boolean
    '''
    if not current_action:
        return True

    valide_actions_map = {
        "data_upload": [],
        "data_transfer": ["download"],
        "data_delete": [],
        "data_download": ["download", "transfer"]
    }

    valide_actions = valide_actions_map[current_action]

    if target_action in valide_actions:
        return True

    return False


async def validate_file_repeated(zone, project_code, location) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Check if file already exists at this location."""

    payload = {
        "page": 0,
        "page_size": 1,
        "partial": False,
        "order_by": "global_entity_id",
        "order_type": "desc",
        "query": {
            "location": location,
            "labels": [zone, 'File'],
            "archived": False,
        }
    }
    url = ConfigClass.NEO4J_SERVICE_V2 + "nodes/query"
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
    if response.status_code == 200:
        result = response.json()['result']
        if len(result) > 0:
            return False, result[0]
    return True, None


async def validate_folder_repeated(zone, project_code, folder_relative_path, name) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Check if folder already exists for this relative path."""

    payload = {
        "page": 0,
        "page_size": 1,
        "partial": False,
        "order_by": "global_entity_id",
        "order_type": "desc",
        "query": {
            "project_code": project_code,
            "folder_relative_path": folder_relative_path,
            "name": name,
            "labels": [zone, 'Folder'],
            "archived": False,
        }
    }
    url = ConfigClass.NEO4J_SERVICE_V2 + "nodes/query"
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
    if response.status_code == 200:
        result = response.json()['result']
        if len(result) > 0:
            return False, result[0]
    return True, None
