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


def get_resource_bygeid(geid, exclude_archived=False) -> Optional[dict]:
    '''
        function will call the neo4j api to get the node
        by geid. raise exception if the geid is not exist
    '''
    url = ConfigClass.NEO4J_SERVICE + "nodes/geid/%s"%geid
    res = requests.get(url)
    nodes = res.json()

    if len(nodes) == 0:
        raise Exception('Not found resource: ' + geid)

    return nodes[0]


def get_files_recursive(folder_geid, all_files=None):
    if all_files is None:
        all_files = []

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
