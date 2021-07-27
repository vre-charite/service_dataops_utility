import os
import time
from config import ConfigClass
import requests
import enum
from resources.helpers import send_message_to_queue, fetch_geid, \
    http_query_node, get_resource_bygeid, get_connected_nodes, location_decoder
from models.base_models import EAPIResponseCode, APIResponse
from models import file_ops_models as models
from commons.data_providers.redis_project_session_job import SessionJob
from .validations import validate_project, validate_file_repeated, validate_folder_repeated

# validation => flatten sources(if source is 'Folder', find all child files) => generate input and output path => send messages


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
    project_code = validation_result.get("code", None)

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

    # validate destination
    destination_geid = data.payload.get('destination', None)
    node_destination = None
    if destination_geid:
        node_destination = get_resource_bygeid(destination_geid)
        node_destination['resource_type'] = get_resource_type(
            node_destination['labels'])
        if not node_destination['resource_type'] in ['Folder', 'Container']:
            return EAPIResponseCode.bad_request, "Invalid destination type: " + destination_geid

    # validate targets
    targets = data.payload["targets"]
    to_validate_repeat_geids = []
    repeated = []

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
                    raise Exception('Invalid target type(only support File or Folder): ' + str(source))
                fetched.append(source)
                to_validate_repeat_geids.append(source['global_entity_id'])
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
        # append path and attrs
        if source["resource_type"] == "Folder":
            nodes_child = get_connected_nodes(
                source['global_entity_id'], "output")
            nodes_child_files = [
                node for node in nodes_child if "File" in node["labels"]]

            # check folder repeated
            target_folder_relative_path = ""
            if node_destination and node_destination['resource_type'] == 'Folder':
                target_folder_relative_path = os.path.join(
                node_destination['folder_relative_path'], node_destination['name'])
            output_folder_name = source.get('rename', source['name'])
            is_valid, found = validate_folder_repeated(
            "VRECore", project_code, target_folder_relative_path, output_folder_name)
            if not is_valid:
                repeated_path = os.path.join(target_folder_relative_path, output_folder_name)
                repeated.append({
                    'error': 'entity-exist',
                    'is_valid': is_valid,
                    "geid": source['global_entity_id'],
                    'found': found['global_entity_id'],
                    'found_name': repeated_path
                })

            # add other attributes
            for node in nodes_child_files:
                node['parent_folder'] = source
                input_nodes = get_connected_nodes(
                    node["global_entity_id"], "input")
                input_nodes = [
                    node for node in input_nodes if 'Folder' in node['labels']]
                input_nodes.sort(key=lambda f: f['folder_level'])
                found_source_node = [
                    node for node in input_nodes if node['global_entity_id'] == source['global_entity_id']][0]
                path_relative_to_source_path = ''
                source_index = input_nodes.index(found_source_node)
                folder_name_list = [node['name']
                                    for node in input_nodes[source_index + 1:]]
                path_relative_to_source_path = os.sep.join(folder_name_list)
                node['path_relative_to_source_path'] = path_relative_to_source_path
                node['ouput_relative_path'] = os.path.join(
                    output_folder_name, path_relative_to_source_path)
            flattened_sources += nodes_child_files

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
            source, node_destination, ouput_relative_path=ouput_relative_path)
        source['input_path'] = input_path
        source['output_path'] = output_path
        # validate repeated
        if source['global_entity_id'] in to_validate_repeat_geids:
            host = "{}://{}".format(ingestion_type, ingestion_host)
            bucket = "core-" + project_info["code"] + "/"
            dest_location = os.path.join(host, bucket + source['output_path'])
            is_valid, found = validate_file_repeated(
                "VRECore", project_code, dest_location)
            if not is_valid:
                repeated.append({
                    'error': 'entity-exist',
                    'is_valid': is_valid,
                    "geid": source['global_entity_id'],
                    'found': found['global_entity_id'],
                    'found_name': source['output_path']
                })
    if len(repeated) > 0:
        return EAPIResponseCode.conflict, repeated

    # job dispatch
    jobs = []
    for source in flattened_sources:
        # init job
        job_geid = fetch_geid()
        neo4j_zone = get_zone(source['labels'])
        session_job = SessionJob(
            data.session_id, project_info["code"], "data_transfer",
            data.operator, task_id=data.task_id)
        session_job.set_job_id(job_geid)
        session_job.set_progress(0)
        session_job.set_source(source['ingestion_path'])
        session_job.set_status(models.EActionState.INIT.name)
        session_job.add_payload("geid", source['global_entity_id'])
        session_job.save()
        jobs.append(session_job)

        try:
            # send message
            generate_id = source.get("generate_id", "undefined")
            succeed_sent = transfer_file_message(_logger,
                                                 data.session_id, job_geid, source['global_entity_id'],
                                                 source["input_path"], source["output_path"],
                                                 project_info['code'], generate_id,
                                                 source['uploader'], data.operator,
                                                 1, destination_geid)
            if not succeed_sent[0]:
                raise(
                    Exception('transfer message sent failed: ' + succeed_sent[1]))
            # update job status
            session_job.add_payload("output_path", source["output_path"])
            session_job.add_payload("input_path", source["input_path"])
            session_job.add_payload("destination_dir_geid", str(destination_geid))
            session_job.add_payload("source_folder", source.get('parent_folder'))
            session_job.add_payload("display_path", source.get('display_path'))
            session_job.set_status(models.EActionState.RUNNING.name)
            session_job.save()
        except Exception as e:
            exception_mesaage = str(e)
            session_job.set_status(models.EActionState.TERMINATED.name)
            session_job.add_payload("error", exception_mesaage)
            session_job.save()

    return EAPIResponseCode.accepted, [job.to_dict() for job in jobs]


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
        output_path = os.path.join(path, ouput_relative_path, copied_name)
        root_folder = path.split('/')[0]
        if not destination:
            output_path = os.path.join(root_folder, ouput_relative_path, copied_name)
        return source_object_name, output_path
