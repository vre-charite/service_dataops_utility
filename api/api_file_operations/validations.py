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
        "Dataset", {"global_entity_id": project_geid})
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


def validate_destination_repeated(zone, project_code, resource_type, full_path):
    '''
    False invalid, True valid
    '''
    # validate destination
    query = {}
    root_path = {
        'Greenroom': ConfigClass.NFS_ROOT_PATH,
        'VRECore': ConfigClass.VRE_ROOT_PATH
    }.get(zone)
    if resource_type == "Folder":
        query['folder_relative_path'] = os.path.dirname(
            full_path).replace(root_path, '').replace(project_code, '', 1).replace('/{}/'.format(project_code), '').strip("/")
        query['name'] = os.path.basename(full_path)
        query['project_code'] = project_code
    if resource_type == "File":
        query['full_path'] = full_path
    payload = {
        "page": 0,
        "page_size": 1,
        "partial": False,
        "order_by": "global_entity_id",
        "order_type": "desc",
        "query": {
            **query,
            "labels": [zone, resource_type]
        }
    }
    url = ConfigClass.NEO4J_SERVICE_V2 + "nodes/query"
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        result = response.json()['result']
        if len(result) > 0:
            return False, result[0]
    # check old raw files
    if resource_type == "File":
        relative_path = full_path.replace(root_path, '').replace(
            '/{}/'.format(project_code), '')
        query['full_path'] = os.path.join(
            root_path, project_code, 'raw', relative_path)
        payload = {
            "page": 0,
            "page_size": 1,
            "partial": False,
            "order_by": "global_entity_id",
            "order_type": "desc",
            "query": {
                **query,
                "labels": [zone, resource_type]
            }
        }
        url = ConfigClass.NEO4J_SERVICE_V2 + "nodes/query"
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            result = response.json()['result']
            if len(result) > 0:
                return False, result[0]
    return True, None
