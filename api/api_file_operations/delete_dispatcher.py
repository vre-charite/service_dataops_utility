import os
import time
from config import ConfigClass
import requests
import enum
from resources.helpers import send_message_to_queue, fetch_geid, http_query_node, get_resource_bygeid, \
    get_connected_nodes, location_decoder, http_update_node
from models.base_models import EAPIResponseCode, APIResponse
from models import file_ops_models as models
from commons.data_providers.redis_project_session_job import SessionJob
from .validations import validate_project
from resources.helpers import send_message_to_queue
from models.resource_lock_mgr import ResourceLockManager


def delete_dispatcher(_logger, data: models.FileOperationsPOST, auth_token):
    '''
    return tuple response_code, worker_result
    '''
    # validate project
    project_validation_code, validation_result = validate_project(
        data.project_geid)
    if project_validation_code != EAPIResponseCode.success:
        return project_validation_code, validation_result
    project_info = validation_result

    # validate payload
    def validate_payload(payload):
        if not type(payload) == dict:
            return False, "payload must be an object"
        if not "targets" in payload:
            return False, "targets required"
        if not type(payload["targets"]) == list:
            return False, "targets must be a list of objects"
        for target in payload["targets"]:
            if "geid" not in target:
                return False, "target must have a valid geid"
        return True, "validated"
    validated, validation_result = validate_payload(data.payload)
    if not validated:
        return EAPIResponseCode.bad_request, "Invalid payload: " + validation_result

    # validate targets
    targets = data.payload["targets"]

    def validate_targets(targets: list):
        fetched = []
        try:
            for target in targets:
                # get source file
                source = get_resource_bygeid(target['geid'])
                if not source:
                    raise Exception('Not found resource: ' + target['geid'])
                if target.get("rename"):
                    source["rename"] = target.get("rename")
                source['resource_type'] = get_resource_type(source['labels'])
                if not source['resource_type'] in ['File', 'Folder']:
                    raise Exception('Invalid target: ' + str(source))
                source['zone'] = get_zone(source['labels'])
                fetched.append(source)
            return True, fetched
        except Exception as err:
            return False, str("validate target failed: " + str(err))
    validated, validation_result = validate_targets(targets)
    if not validated:
        return EAPIResponseCode.bad_request, validation_result

    sources = validation_result

    flattened_sources = [
        node for node in sources if node['resource_type'] == "File"]
    # flatten sources
    for source in sources:
        if source["resource_type"] == "Folder":
            # if folder, send message immediately
            zone = [label for label in source["labels"]
                    if label in ["Greenroom", "VRECore"]][0]
            payload_zone = get_payload_zone(zone)
            frontend_zone = get_frontend_zone(payload_zone)
            # output_folder_name = source['name'] + "_" + str(round(time.time()))
            # # update folder name and relative path of the original fnodes
            # update_json = {
            #     'archived': True,
            #     'name': output_folder_name
            # }
            # updated_source_node = http_update_node(
            #     "Folder", source['id'], update_json=update_json)
            # if updated_source_node.status_code != 200:
            #     raise Exception("updated_source_ndoe error: " + updated_source_node.text
            #                     + "----- payload: " + str(update_json))
            # res = updated_source_node.json()[0]
            # refresh_node(source, res)
            # nodes_child = get_connected_nodes(
            #     source['global_entity_id'], "output")
            # nodes_child_files = [
            #     node for node in nodes_child if "File" in node["labels"]]

            # init the folder delete job here, please note the KEYWORD for redis
            # is same with file delete as `data_delete` to save api calling
            job_geid = fetch_geid()
            session_job = SessionJob(
                data.session_id, project_info["code"], "data_delete",
                data.operator, task_id=data.task_id)
            session_job.set_job_id(job_geid)
            session_job.set_progress(0)
            session_job.set_source(source['display_path'])
            session_job.set_status(models.EActionState.RUNNING.name)
            session_job.add_payload("geid", source['global_entity_id'])
            session_job.add_payload("zone", payload_zone)
            session_job.add_payload("frontend_zone", frontend_zone)
            session_job.add_payload("display_path", source.get('display_path'))
            send_folder_message(
                _logger,
                data.session_id,
                job_geid,
                source['global_entity_id'],
                project_info['code'],
                source['uploader'],
                data.operator,
                payload_zone,
                auth_token
            )
            session_job.save()
        elif source["resource_type"] == "File":
            # Get new name
            source_name, source_extension = os.path.splitext(source['name'])
            new_file_name = source_name + '_' + \
                str(round(time.time())) + source_extension
            source["rename"] = new_file_name

    # update input output path
    for source in flattened_sources:
        source['resource_type'] = get_resource_type(source['labels'])
        location = source['location']
        ingestion_type, ingestion_host, ingestion_path = location_decoder(
            location)
        source['ingestion_type'] = ingestion_type
        source['ingestion_host'] = ingestion_host
        source['ingestion_path'] = ingestion_path
        ouput_relative_path = source.get('ouput_relative_path', '')
        input_path, output_path = get_output_payload(
            source, None, ouput_relative_path=ouput_relative_path)
        source['input_path'] = input_path
        source['output_path'] = output_path
        # will unlock when k8s job done, in pipelinewatch
        lock_succeed = try_lock(ingestion_path)
        if not lock_succeed:
            return EAPIResponseCode.bad_request, [
                {
                    'error': 'operation-block',
                    'is_valid': False,
                    "blocked": ingestion_path
                }
            ]


    # job dispatch
    jobs = []
    for source in flattened_sources:
        # init job
        job_geid = fetch_geid()
        session_job = SessionJob(
            data.session_id, project_info["code"], "data_delete",
            data.operator, task_id=data.task_id)
        session_job.set_job_id(job_geid)
        session_job.set_progress(0)
        session_job.set_source(source['ingestion_path'])
        session_job.set_status(models.EActionState.INIT.name)
        session_job.add_payload("geid", source['global_entity_id'])
        session_job.save()
        jobs.append(session_job)

        try:
            # check namespace
            zone = [label for label in source["labels"]
                    if label in ["Greenroom", "VRECore"]][0]
            payload_zone = get_payload_zone(zone)
            frontend_zone = get_frontend_zone(payload_zone)
            # Send message to the queue
            message_payload = {
                "event_type": "file_delete",
                "payload": {
                    "session_id": data.session_id,
                    "job_id": job_geid,
                    "operator": data.operator,
                    "input_path": source["input_path"],
                    "input_geid": source['global_entity_id'],
                    "output_path": source['output_path'],
                    "trash_path": "",
                    "generate_id": source.get('generate_id', 'undefined'),
                    "generic": True,
                    "uploader": source.get("uploader", ""),
                    "namespace": payload_zone,
                    "project": project_info["code"],
                    "auth_token": auth_token,
                },
                "create_timestamp": time.time()
            }
            res = send_message_to_queue(message_payload)
            _logger.info(res)
            _logger.info(message_payload)
            # pop out the credentials in the return
            message_payload["payload"].pop("auth_token")

            session_job.set_status(models.EActionState.RUNNING.name)
            session_job.add_payload("zone", payload_zone)
            session_job.add_payload("frontend_zone", frontend_zone)
            session_job.add_payload("message_sent", message_payload)
            session_job.add_payload("source_folder", source.get("source_folder", None))
            session_job.add_payload("child_index", source.get("child_index", None))
            session_job.add_payload("display_path", source.get('display_path'))
            session_job.save()
        except Exception as e:
            exception_mesaage = str(e)
            session_job.set_status(models.EActionState.TERMINATED.name)
            session_job.add_payload("error", exception_mesaage)
            session_job.save()

    return EAPIResponseCode.accepted, [job.to_dict() for job in jobs]

def send_folder_message(_logger, session_id, job_id, input_geid, project_code,
                        uploader, operator, payload_zone, auth_token):
    message_payload = {
        "event_type": "folder_delete",
        "payload": {
            "session_id": session_id,
            "job_id": job_id,
            "operator": operator,
            "input_path": input_geid,
            "input_geid": input_geid,
            "output_path": "",
            "trash_path": "",
            "generic": True,
            "uploader": uploader,
            "namespace": payload_zone,
            "project": project_code,
            "auth_token": auth_token,
        },
        "create_timestamp": time.time()
    }
    url = ConfigClass.SEND_MESSAGE_URL
    _logger.info("Sending Message To Queue: " + str(message_payload))
    res = requests.post(
        url=url,
        json=message_payload,
        headers={"Content-type": "application/json; charset=utf-8"}
    )
    return res.status_code == 200, res.text

def get_payload_zone(zone: str):
    return {
        "VRECore": "vrecore",
        "Greenroom": "greenroom"
    }.get(zone)


def get_frontend_zone(my_payload_zone: str):
    '''
    disk namespace to path
    '''
    return {
        "greenroom": "Green Room",
        "vre": "VRE Core",
        "vrecore": "VRE Core"
    }.get(my_payload_zone, None)


def get_resource_type(labels: list):
    '''
    Get resource type by neo4j labels
    '''
    resources = ['File', 'TrashFile', 'Folder', 'Container']
    for label in labels:
        if label in resources:
            return label
    return None


def get_zone(labels: list):
    '''
    Get resource type by neo4j labels
    '''
    zones = ['Greenroom', 'VRECore']
    for label in labels:
        if label in zones:
            return label
    return None

def get_output_payload(file_node, destination=None, ouput_relative_path=''):
    '''
    return inputpath, outputpath
    '''
    location = file_node['location']
    splits_loaction = location.split("://")
    ingestion_type = file_node['ingestion_type']
    ingestion_host = file_node['ingestion_host']
    ingestion_path = file_node['ingestion_path']
    if ingestion_type == "minio":
        splits_ingestion = ingestion_path.split("/", 1)
        source_bucket_name = splits_ingestion[0]
        source_object_name = splits_ingestion[1]
        path, source_name = os.path.split(source_object_name)
        if destination and destination['resource_type'] == 'Folder':
            path = os.path.join(
                destination['folder_relative_path'], destination['name'])
        copied_name = file_node['rename'] if file_node.get(
            'rename') else source_name
        output_path = os.path.join(ouput_relative_path, copied_name)
        return location, output_path

def refresh_node(target: dict, new: dict):
    for k, v in new.items():
        target[k] = v

def try_lock(resource_key):
    # lock manager
    rlock_mgr = ResourceLockManager()
    result = rlock_mgr.check_lock(resource_key, 'default')
    locked=  True if result else False
    if not locked:
        rlock_mgr.lock(resource_key, 'default')
        return True
    else:
        # currently in other operations
        return False
