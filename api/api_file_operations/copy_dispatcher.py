import enum
import os
import time
from enum import Enum
from enum import unique
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import requests

from api.api_file_operations.dispatcher import BaseDispatcher
from api.api_file_operations.validations import validate_project
from commons.data_providers.redis_project_session_job import SessionJob
from config import ConfigClass
from models import file_ops_models as models
from models.base_models import EAPIResponseCode
from resources.helpers import fetch_geid
from resources.helpers import get_resource_bygeid
from resources.helpers import location_decoder


@unique
class ResourceType(str, Enum):
    FOLDER = 'Folder'
    FILE = 'File'
    TRASH_FILE = 'TrashFile'
    CONTAINER = 'Container'


class Source(dict):
    """Store information about one source."""


class SourceList(list):
    """Store list of Sources."""

    def __init__(self, sources: List[Dict[str, Any]]) -> None:
        super().__init__([Source(source) for source in sources])

    def _get_by_resource_type(self, resource_type: ResourceType) -> List[Source]:
        return [source for source in self if source['resource_type'] == resource_type]

    def filter_folders(self) -> List[Source]:
        """Return sources with folder resource type."""
        return self._get_by_resource_type(ResourceType.FOLDER)

    def filter_files(self) -> List[Source]:
        """Return sources with file resource type."""
        return self._get_by_resource_type(ResourceType.FILE)


class CopyDispatcher(BaseDispatcher):
    """Validate targets, create copy file/folder sessions and send messages to the queue."""

    def execute(
        self, _logger, data: models.FileOperationsPOST, auth_token: Dict[str, str]
    ) -> Tuple[EAPIResponseCode, Union[str, List[Dict[str, Any]]]]:
        """Execute copy logic."""

        project_validation_code, validation_result = validate_project(data.project_geid)
        if project_validation_code != EAPIResponseCode.success:
            return project_validation_code, validation_result
        project_info = validation_result

        payload = data.payload.dict()

        # validate destination
        destination_geid = payload.get('destination', None)
        if destination_geid:
            node_destination = get_resource_bygeid(destination_geid)
            if not node_destination:
                raise Exception(f'Not found resource: {destination_geid}')
            node_destination['resource_type'] = get_resource_type(node_destination['labels'])
            if not node_destination['resource_type'] in [ResourceType.FOLDER, ResourceType.CONTAINER]:
                return EAPIResponseCode.bad_request, f'Invalid destination type: {destination_geid}'
        else:
            return EAPIResponseCode.bad_request, f'Destination is required: {destination_geid}'

        targets = payload['targets']

        def validate_targets(targets: List[Dict[str, Any]]):
            fetched = []
            try:
                for target in targets:
                    # get source file
                    source = get_resource_bygeid(target['geid'])
                    if not source:
                        raise Exception(f'Not found resource: {target["geid"]}')
                    if source['archived'] is True:
                        raise Exception(f'Archived files should not perform further file actions: {target["geid"]}')
                    source['resource_type'] = get_resource_type(source['labels'])
                    if not source['resource_type'] in ['File', 'Folder']:
                        raise Exception(f'Invalid target type (only support File or Folder): {str(source)}')
                    fetched.append(source)
                return True, fetched
            except Exception as err:
                return False, str("validate target failed: " + str(err))

        validated, validation_result = validate_targets(targets)
        if not validated:
            return EAPIResponseCode.bad_request, validation_result

        sources = SourceList(validation_result)

        jobs = []

        sources_folders = sources.filter_folders()
        for source in sources_folders:
            # append path and attrs
            source_bk = "gr-" + project_info["code"]
            source_path = os.path.join(source_bk, source['folder_relative_path'], source['name'])

            job_geid = fetch_geid()
            session_job = SessionJob(
                data.session_id, project_info['code'], 'data_transfer', data.operator, task_id=data.task_id
            )

            try:
                session_job.set_job_id(job_geid)
                session_job.set_progress(0)
                session_job.set_source(source_path)
                session_job.set_status(models.EActionState.RUNNING.name)
                session_job.add_payload('geid', source['global_entity_id'])
                transfer_folder_message(
                    _logger,
                    data.session_id,
                    job_geid,
                    source['global_entity_id'],
                    project_info['code'],
                    str(data.payload.request_id or ''),
                    source['uploader'],
                    data.operator,
                    destination_geid,
                    auth_token,
                    source['name'],
                )
                session_job.save()
                jobs.append(session_job)
            except Exception as e:
                exception_message = str(e)
                session_job.set_status(models.EActionState.TERMINATED.name)
                session_job.add_payload('error', exception_message)
                session_job.save()

        sources_files = sources.filter_files()
        for source in sources_files:
            source['resource_type'] = get_resource_type(source['labels'])
            ingestion_type, ingestion_host, ingestion_path = location_decoder(source['location'])
            source['ingestion_type'] = ingestion_type
            source['ingestion_host'] = ingestion_host
            source['ingestion_path'] = ingestion_path
            ouput_relative_path = source.get('ouput_relative_path', '')
            input_path, output_path = get_output_payload(source, node_destination, ouput_relative_path=ouput_relative_path)
            source['input_path'] = input_path
            source['output_path'] = output_path

            job_geid = fetch_geid()
            session_job = SessionJob(
                data.session_id, project_info['code'], 'data_transfer', data.operator, task_id=data.task_id
            )
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
                succeed_sent = transfer_file_message(
                    _logger,
                    data.session_id,
                    job_geid,
                    source['global_entity_id'],
                    source['input_path'],
                    source['output_path'],
                    project_info['code'],
                    str(data.payload.request_id or ''),
                    generate_id,
                    source['uploader'],
                    data.operator,
                    1,
                    destination_geid,
                    auth_token,
                )
                if not succeed_sent[0]:
                    raise Exception('transfer message sent failed: ' + succeed_sent[1])
                # update job status
                session_job.add_payload("output_path", source["output_path"])
                session_job.add_payload("input_path", source["input_path"])
                session_job.add_payload("destination_dir_geid", str(destination_geid))
                session_job.add_payload("source_folder", source.get('parent_folder'))
                session_job.add_payload("display_path", source.get('display_path'))
                session_job.set_status(models.EActionState.RUNNING.name)
                session_job.save()
            except Exception as e:
                exception_message = str(e)
                session_job.set_status(models.EActionState.TERMINATED.name)
                session_job.add_payload("error", exception_message)
                session_job.save()

        return EAPIResponseCode.accepted, [job.to_dict() for job in jobs]


def transfer_folder_message(
    _logger,
    session_id,
    job_id,
    input_geid,
    project_code,
    request_id: Optional[str],
    uploader,
    operator,
    destination_geid,
    auth_token,
    rename,
) -> Tuple[bool, str]:
    payload = {
        'event_type': 'folder_copy',
        'payload': {
            'session_id': session_id,
            'job_id': job_id,
            'input_geid': input_geid,
            'project': project_code,
            'request_id': request_id,
            'uploader': uploader,
            'generic': True,
            'operator': operator,
            'destination_geid': destination_geid,
            'auth_token': auth_token,
            'process_pipeline': 'data_transfer_folder',
            'rename': rename
        },
        'create_timestamp': time.time()
    }
    url = ConfigClass.SEND_MESSAGE_URL
    _logger.info("Sending Message To Queue: " + str(payload))
    res = requests.post(
        url=url,
        json=payload,
        headers={"Content-type": "application/json; charset=utf-8"}
    )
    return res.status_code == 200, res.text


def transfer_file_message(
    _logger,
    session_id,
    job_id,
    input_geid,
    input_path,
    output_path,
    project_code,
    request_id: Optional[str],
    generate_id,
    uploader,
    operator,
    operation_type: int,
    destination_geid,
    auth_token,
) -> Tuple[bool, str]:
    my_generate_id = generate_id if generate_id else 'undefined'
    payload = {
        'event_type': 'file_copy',
        'payload': {
            'session_id': session_id,
            'job_id': job_id,
            'input_geid': input_geid,
            'input_path': input_path,
            'output_path': output_path,
            'operation_type': operation_type,
            'project': project_code,
            'request_id': request_id,
            'generate_id': my_generate_id,
            'uploader': uploader,
            'generic': True,
            'operator': operator,
            'destination_geid': destination_geid,
            'auth_token': auth_token
        },
        'create_timestamp': time.time()
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


def interpret_operation_location(file_name, project, destination) -> str:
    return os.path.join(ConfigClass.VRE_ROOT_PATH, project, destination, file_name)


def get_resource_type(labels: list) -> str:
    '''
    Get resource type by neo4j labels
    '''
    resources = ['File', 'TrashFile', 'Folder', 'Container']
    for label in labels:
        if label in resources:
            return label
    return None


def get_zone(labels: list) -> str:
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
