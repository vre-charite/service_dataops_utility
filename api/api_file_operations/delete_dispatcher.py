import os
import subprocess
import time
from config import ConfigClass
import requests
import enum
from resources.helpers import send_message_to_queue, fetch_geid, http_query_node, get_resource_bygeid
from models.base_models import EAPIResponseCode, APIResponse
from models import file_ops_models as models
from commons.data_providers.redis_project_session_job import SessionJob, session_job_get_status, session_job_delete_status
from .validations import validate_project
from resources.helpers import send_message_to_queue


def delete_dispatcher(_logger, data: models.FileOperationsPOST):
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
                if target.get("rename"):
                    source["rename"] = target.get("rename")
                source['resource_type'] = get_resource_type(source['labels'])
                if not source['resource_type'] in ['File', 'Folder']:
                    raise Exception('Invalid target: ' + str(source))
                source['zone'] = get_zone(source['labels'])
                source['full_path'] = get_full_path(
                    source, project_info['code'])
                fetched.append(source)
            return True, fetched
        except Exception as err:
            return False, str("validate target failed: " + str(err))

    validated, validation_result = validate_targets(targets)
    if not validated:
        return EAPIResponseCode.bad_request, validation_result

    # job dispatch
    sources = validation_result
    jobs = []
    for source in sources:
        # init job
        job_geid = fetch_geid()
        session_job = SessionJob(
            data.session_id, project_info["code"], "data_delete",
            data.operator, task_id=data.task_id)
        session_job.set_job_id(job_geid)
        session_job.set_progress(0)
        session_job.set_source(source["full_path"])
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
            disk_path = {
                "Greenroom": ConfigClass.NFS_ROOT_PATH,
                "VRECore": ConfigClass.VRE_ROOT_PATH
            }.get(zone)
            # Get new name
            source_name, source_extension = os.path.splitext(source['name'])
            new_file_name = source_name + '_' + \
                str(round(time.time())) + source_extension
            # Send message to the queue
            message_payload = {
                "event_type": "file_delete",
                "payload": {
                    "session_id": data.session_id,
                    "job_id": job_geid,
                    "operator": data.operator,
                    "input_path": source["full_path"],
                    "input_geid": source['global_entity_id'],
                    "output_path": disk_path + "/TRASH/" + project_info["code"] + "/" + new_file_name,
                    "trash_path": disk_path + "/TRASH",
                    "generate_id": source.get('generate_id', 'undefined'),
                    "generic": True,
                    "uploader": source.get("uploader", ""),
                    "namespace": payload_zone,
                    "project": project_info["code"],
                },
                "create_timestamp": time.time()
            }
            res = send_message_to_queue(message_payload)
            session_job.set_status(models.EActionState.RUNNING.name)
            session_job.add_payload("zone", payload_zone)
            session_job.add_payload("frontend_zone", frontend_zone)
            session_job.save()
        except Exception as e:
            exception_mesaage = str(e)
            session_job.set_status(models.EActionState.TERMINATED.name)
            session_job.add_payload("error", exception_mesaage)
            session_job.save()

    return EAPIResponseCode.accepted, [job.to_dict() for job in jobs]


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
    resources = ['File', 'TrashFile', 'Folder', 'Dataset']
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


def get_full_path(resource, project_code):
    try:
        if resource['resource_type'] == 'File':
            return resource['full_path']
        if resource['resource_type'] == 'Folder':
            return {
                'Greenroom': os.path.join(ConfigClass.NFS_ROOT_PATH, project_code, 'raw',
                                          resource['folder_relative_path'], resource['name']),
                'VRECore': os.path.join(ConfigClass.VRE_ROOT_PATH, project_code,
                                        resource['folder_relative_path'], resource['name']),
            }.get(resource['zone'])
    except Exception as e:
        raise Exception('Invalid entity: ' +
                        str(resource) + '-------' + str(e))
