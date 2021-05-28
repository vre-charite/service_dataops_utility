from config import ConfigClass
import requests

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
    primary_label i.e. Folder, File, Dataset
    '''
    payload = {
        **query_params
    }
    node_query_url = ConfigClass.NEO4J_SERVICE + "nodes/{}/query".format(primary_label)
    response = requests.post(node_query_url, json=payload)
    return response

def get_resource_bygeid(geid):
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
            "labels": ['Dataset']
        }
    }
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
    raise Exception('Not found resource: ' + geid)


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