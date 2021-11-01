from config import ConfigClass
import requests
import re
from typing import Optional

def fetch_geid(id_type=""):
    ## fetch global entity id
    entity_id_url = ConfigClass.UTILITY_SERVICE + "/v1/utility/id?entity_type={}".format(id_type)
    respon_entity_id_fetched = requests.get(entity_id_url)
    if respon_entity_id_fetched.status_code == 200:
        pass
    else:
        raise Exception('Entity id fetch failed: ' + entity_id_url + ": " + str(respon_entity_id_fetched.text))
    trash_geid = respon_entity_id_fetched.json()['result']
    return trash_geid

def send_message_to_queue(payload):
    url = ConfigClass.SEND_MESSAGE_URL
    res = requests.post(
        url=url,
        json=payload,
        headers={"Content-type": "application/json; charset=utf-8"}
    )
    print(res.status_code)
    return res.status_code == 200

def http_query_node(primary_label, query_params={}):
    '''
    primary_label i.e. Folder, File, Container
    '''
    payload = {
        **query_params
    }
    node_query_url = ConfigClass.NEO4J_SERVICE + "nodes/{}/query".format(primary_label)
    response = requests.post(node_query_url, json=payload)
    return response

# TODO: usage of this function could be improved with better error handling
def get_resource_bygeid(geid, exclude_archived=False) -> Optional[dict]:
    '''
    if not exist return None
    '''
    url = ConfigClass.NEO4J_SERVICE_V2 + "nodes/query"
    payload_file = {
        "page": 0,
        "page_size": 1,
        "partial": False,
        "order_by": "global_entity_id",
        "order_type": "desc",
        "query": {
            "global_entity_id": geid,
            "labels": ['File']
        }
    }
    payload_folder = {
        "page": 0,
        "page_size": 1,
        "partial": False,
        "order_by": "global_entity_id",
        "order_type": "desc",
        "query": {
            "global_entity_id": geid,
            "labels": ['Folder']
        }
    }
    payload_project = {
        "page": 0,
        "page_size": 1,
        "partial": False,
        "order_by": "global_entity_id",
        "order_type": "desc",
        "query": {
            "global_entity_id": geid,
            "labels": ['Container']
        }
    }
    if exclude_archived:
        payload_project["query"]["archived"] = False
        payload_folder["query"]["archived"] = False
        payload_file["query"]["archived"] = False
    response_file = requests.post(url, json=payload_file)
    if response_file.status_code == 200:
        result = response_file.json()['result']
        if len(result) > 0:
            return result[0]
    response_folder = requests.post(url, json=payload_folder)
    if response_folder.status_code == 200:
        result = response_folder.json()['result']
        if len(result) > 0:
            return result[0]
    response_project = requests.post(url, json=payload_project)
    if response_project.status_code == 200:
        result = response_project.json()['result']
        if len(result) > 0:
            return result[0]
    return None


def get_files_recursive(folder_geid, all_files=[]):
    query = {
        "start_label": "Folder",
        "end_labels": ["File", "Folder"],
        "query": {
            "start_params": {
                "global_entity_id": folder_geid,
            },
            "end_params": {
            }
        }
    }
    resp = requests.post(ConfigClass.NEO4J_SERVICE_V2 + "relations/query", json=query)
    for node in resp.json()["results"]:
        if "File" in node["labels"]:
            all_files.append(node)
        else:
            get_files_recursive(node["global_entity_id"], all_files=all_files)
    return all_files


def get_resource_type(labels: list):
    '''
    Get resource type by neo4j labels
    '''
    resources = ['File', 'TrashFile', 'Folder', 'Container']
    for label in labels:
        if label in resources:
            return label
    return None

def get_connected_nodes(geid, direction: str = "both"):
    '''
    return a list of nodes
    '''
    if direction == 'both':
        params = {
            "direction": "input"
        }
        url = ConfigClass.NEO4J_SERVICE + "relations/connected/{}".format(geid)
        response = requests.get(url, params=params)
        if response.status_code != 200:
            raise Exception('Internal error for neo4j service, \
                when get_connected, geid: ' + str(geid))
        connected_nodes = response.json()['result']
        params = {
            "direction": "output"
        }
        url = ConfigClass.NEO4J_SERVICE + "relations/connected/{}".format(geid)
        response = requests.get(url, params=params)
        if response.status_code != 200:
            raise Exception('Internal error for neo4j service, \
                when get_connected, geid: ' + str(geid))
        return connected_nodes + response.json()['result']
    params = {
        "direction": direction
    }
    url = ConfigClass.NEO4J_SERVICE + "relations/connected/{}".format(geid)
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception('Internal error for neo4j service, \
            when get_connected, geid: ' + str(geid))
    connected_nodes = response.json()['result']
    return connected_nodes

def location_decoder(location: str):
    '''
    decode resource location
    return ingestion_type, ingestion_host, ingestion_path
    '''
    splits_loaction = location.split("://", 1)
    ingestion_type = splits_loaction[0]
    ingestion_url = splits_loaction[1]
    path_splits =  re.split(r"(?<!/)/(?!/)", ingestion_url, 1)
    ingestion_host = path_splits[0]
    ingestion_path = path_splits[1]
    return ingestion_type, ingestion_host, ingestion_path

def http_update_node(primary_label, neo4j_id, update_json):
    # update neo4j node
    update_url = ConfigClass.NEO4J_SERVICE + \
        "nodes/{}/node/{}".format(primary_label, neo4j_id)
    res = requests.put(url=update_url, json=update_json)
    return res
