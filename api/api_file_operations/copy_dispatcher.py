# Copyright 2022 Indoc Research
# 
# Licensed under the EUPL, Version 1.2 or – as soon they
# will be approved by the European Commission - subsequent
# versions of the EUPL (the "Licence");
# You may not use this work except in compliance with the
# Licence.
# You may obtain a copy of the Licence at:
# 
# https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12
# 
# Unless required by applicable law or agreed to in
# writing, software distributed under the Licence is
# distributed on an "AS IS" basis,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied.
# See the Licence for the specific language governing
# permissions and limitations under the Licence.
# 

import os
import time
from typing import Any
from typing import Dict
from typing import List
from typing import Tuple
from typing import Union
import httpx
from api.api_file_operations.dispatcher import BaseDispatcher
from api.api_file_operations.validations import validate_project
from config import ConfigClass
from models import file_ops_models as models
from models.base_models import EAPIResponseCode
from resources.helpers import fetch_geid
from resources.redis_project_session_job import SessionJob


class CopyDispatcher(BaseDispatcher):
    """Validate targets, create copy file/folder sessions and send messages to the queue."""

    async def execute(
        self, _logger, data: models.FileOperationsPOST, auth_token: Dict[str, str]
    ) -> Tuple[EAPIResponseCode, Union[str, List[Dict[str, Any]]]]:
        """Execute copy logic."""

        project_validation_code, validation_result = await validate_project(data.project_geid)
        if project_validation_code != EAPIResponseCode.success:
            return project_validation_code, validation_result
        project_info = validation_result

        if not await self.is_valid_folder_node(data.payload.source):
            return EAPIResponseCode.bad_request, f'Invalid source: {data.payload.source}'

        if not await self.is_valid_folder_node(data.payload.destination):
            return EAPIResponseCode.bad_request, f'Invalid destination: {data.payload.destination}'

        try:
            targets = await self.validate_targets(data.payload.targets)
        except ValueError as e:
            return EAPIResponseCode.bad_request, str(e)

        job_geid = fetch_geid()
        session_job = SessionJob(
            data.session_id, project_info['code'], 'data_transfer', data.operator, task_id=data.task_id
        )

        try:
            await session_job.set_job_id(job_geid)
            session_job.set_progress(0)
            session_job.set_source(', '.join(targets.names))
            session_job.set_status(models.EActionState.RUNNING.name)
            session_job.add_payload('source', data.payload.source)
            session_job.add_payload('destination', data.payload.destination)
            session_job.add_payload('targets', list(targets.geids))
            payload = {
                'event_type': 'folder_copy',
                'payload': {
                    'session_id': data.session_id,
                    'job_id': job_geid,
                    'source_geid': data.payload.source,
                    'include_geids': list(targets.geids),
                    'project': project_info['code'],
                    'request_id': str(data.payload.request_id or ''),
                    'generic': True,
                    'operator': data.operator,
                    'destination_geid': data.payload.destination,
                    'auth_token': auth_token,
                },
                'create_timestamp': time.time(),
            }
            _logger.info('Sending Message To Queue: ' + str(payload))
            async with httpx.AsyncClient() as client:
                response = await client.post(url=ConfigClass.SEND_MESSAGE_URL, json=payload)
            _logger.info(f'Message To Queue has been sent: {response.text}')
            await session_job.save()
        except Exception as e:
            exception_message = str(e)
            session_job.set_status(models.EActionState.TERMINATED.name)
            session_job.add_payload('error', exception_message)
            await session_job.save()

        return EAPIResponseCode.accepted, [session_job.to_dict()]


def get_resource_type(labels: list) -> str:
    """Get resource type by neo4j labels."""

    resources = ['File', 'TrashFile', 'Folder', 'Container']
    for label in labels:
        if label in resources:
            return label
    return None


def get_zone(labels: list) -> str:
    """Get zone by neo4j labels."""

    zones = [ConfigClass.GREEN_ZONE_LABEL, ConfigClass.CORE_ZONE_LABEL]
    for label in labels:
        if label in zones:
            return label
    return None


def get_output_payload(file_node, destination=None, ouput_relative_path=''):
    ingestion_type = file_node['ingestion_type']
    ingestion_path = file_node['ingestion_path']
    if ingestion_type == 'minio':
        splits_ingestion = ingestion_path.split('/', 1)
        source_object_name = splits_ingestion[1]
        path, source_name = os.path.split(source_object_name)
        if destination and destination['resource_type'] == 'Folder':
            path = os.path.join(destination['folder_relative_path'], destination['name'])
        copied_name = file_node['rename'] if file_node.get('rename') else source_name
        output_path = os.path.join(path, ouput_relative_path, copied_name)
        root_folder = path.split('/')[0]
        if not destination:
            output_path = os.path.join(root_folder, ouput_relative_path, copied_name)
        return source_object_name, output_path
