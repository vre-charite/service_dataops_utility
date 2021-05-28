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
from .validations import validate_project, validate_destination_repeated


def copy_dispatcher(_logger, data: models.FileOperationsPOST):
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
            data.session_id, project_info["code"], "data_transfer",
            data.operator, task_id=data.task_id)
        session_job.set_job_id(job_geid)
        session_job.set_progress(0)
        session_job.set_source(source["full_path"])
        session_job.set_status(models.EActionState.INIT.name)
        session_job.add_payload("geid", source['global_entity_id'])
        session_job.save()
        jobs.append(session_job)

        try:
            copied_name = source.get("rename", source['name'])
            destination = get_copy_destination_path(
                project_info['code'], copied_name, data.payload.get('destination', None))
            # validate destination
            is_valid, found = validate_destination_repeated(
                "VRECore", project_info['code'], source['resource_type'], destination)
            if not is_valid:
                raise(Exception('entity-exist'))

            # send message
            generate_id = source.get("generate_id", "undefined")
            succeed_sent = transfer_file_message(_logger,
                                                 data.session_id, job_geid, source['global_entity_id'],
                                                 source["full_path"], destination,
                                                 project_info['code'], generate_id,
                                                 source['uploader'], data.operator, 1, data.payload.get('destination', None))
            if not succeed_sent[0]:
                raise(
                    Exception('transfer message sent failed: ' + succeed_sent[1]))
            # update job status
            session_job.add_payload("destination", destination)
            session_job.add_payload("destination_dir_geid", data.payload.get('destination', None))
            session_job.set_status(models.EActionState.RUNNING.name)
            session_job.save()
        except Exception as e:
            exception_mesaage = str(e)
            session_job.set_status(models.EActionState.TERMINATED.name)
            session_job.add_payload("error", exception_mesaage)
            session_job.save()

    return EAPIResponseCode.accepted, [job.to_dict() for job in jobs]


def transfer_file(_logger, input_path, output_path):
    try:
        output_dir = os.path.dirname(output_path)
        output_file_name = os.path.basename(output_path)
        if os.path.exists(output_path):
            os.remove(output_path)
            _logger.info('remove existed output file: {}'.format(output_path))

        _logger.info('start transfer file {} to {}'.format(
            input_path, output_path))

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            _logger.info('creating output directory: {}'.format(output_dir))

        if os.path.isdir(input_path):
            _logger.info('starting to copy directory: {}'.format(input_path))
        else:
            _logger.info('starting to copy file: {}'.format(input_path))
        subprocess.call(
            ['rsync', '-avz', '--min-size=1', input_path, output_path])
        # shutil.copyfile(input_path, output_path)
        # store_file_meta_data(output_path, output_file_name, input_path, pipeline_name)
        # create_lineage(input_path, output_path, 'testpipeline', pipeline_name, 'test pipeline', datetime.datetime.utcnow().isoformat())
        _logger.info('Successfully copied file from {} to {}'.format(
            input_path, output_path))
    except Exception as e:
        _logger.error('Failed to copy file from {} to {}\n {}'.format(
            input_path, output_path, str(e)))


def transfer_file_message(_logger, session_id, job_id, input_geid, input_path, output_path, project_code,
                          generate_id, uploader, operator, operation_type: int, destination_geid):
    my_generate_id = generate_id if generate_id else 'undefined'
    file_name = os.path.basename(input_path)
    payload = {
        "event_type": "file_copy",
        "payload": {
            "session_id": session_id,
            "job_id": job_id,
            "input_geid": input_geid,
            "input_path": input_path,
            "output_path": output_path,
            "operation_type": operation_type,
            "project": project_code,
            "generate_id": my_generate_id,
            "uploader": uploader,
            "generic": True,
            "operator": operator,
            "destination_geid": destination_geid
        },
        "create_timestamp": time.time()
    }
    url = ConfigClass.SEND_MESSAGE_URL
    _logger.info("Sending Message To Queue: " + str(payload))
    res = requests.post(
        url=url,
        json=payload,
        headers={"Content-type": "application/json; charset=utf-8"}
    )
    return res.status_code == 200, res.text


class EOperationType(enum.Enum):
    A = 0  # copy to greenroom RAW, straight copy ConfigClass.NFS_ROOT_PATH + '/' + self.project + '/processed/' + file_name
    B = 1  # copy to vre core RAW, publish data to vre ConfigClass.VRE_ROOT_PATH + '/' + self.project + '/raw/' + filename


def interpret_operation_location(file_name, project, destination):
    return os.path.join(ConfigClass.VRE_ROOT_PATH, project, destination, file_name)


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


def get_copy_destination_path(project_code, copied_name, destination_geid=None):
    # get copy destination
    print(destination_geid)
    destination = ''
    if destination_geid:
        destination_node = get_resource_bygeid(destination_geid)
        destination_node['resource_type'] = get_resource_type(
            destination_node['labels'])
        if not destination_node['resource_type'] in ['Folder', 'Dataset']:
            raise Exception(
                'Invalid destination, must be a folder or project.')
        if destination_node['resource_type'] == 'Folder':
            destination = os.path.join(
                destination_node['folder_relative_path'], destination_node['name'])
    destination = interpret_operation_location(
        copied_name, project_code, destination)
    return destination
