import requests
import os
from config import ConfigClass
from models.base_models import EAPIResponseCode, APIResponse
from resources.helpers import send_message_to_queue, fetch_geid, http_query_node, get_resource_bygeid


def validate_project(project_geid):
    '''
    validate project info, return tulpe(response_code, errormessage/project_info)
    '''
    # validate project
    project_res = http_query_node(
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


def validate_file_repeated(zone, project_code, location):
    '''
    False invalid, True valid
    '''
    # validate destination
    payload = {
        "page": 0,
        "page_size": 1,
        "partial": False,
        "order_by": "global_entity_id",
        "order_type": "desc",
        "query": {
            "location": location,
            "labels": [zone, 'File']
        }
    }
    url = ConfigClass.NEO4J_SERVICE_V2 + "nodes/query"
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        result = response.json()['result']
        if len(result) > 0:
            return False, result[0]
    return True, None


def validate_folder_repeated(zone, project_code, folder_relative_path, name):
    '''
    False invalid, True valid
    '''
    # validate destination
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
            "labels": [zone, 'Folder']
        }
    }
    url = ConfigClass.NEO4J_SERVICE_V2 + "nodes/query"
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        result = response.json()['result']
        if len(result) > 0:
            return False, result[0]
    return True, None
