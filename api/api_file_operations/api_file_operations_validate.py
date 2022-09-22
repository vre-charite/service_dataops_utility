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

from fastapi import APIRouter
from fastapi_utils.cbv import cbv
from logger import LoggerFactory

from api.api_file_operations.validation_copy import repeated_check
from api.api_file_operations.validations import validate_operation
from api.api_file_operations.validations import validate_project
from config import ConfigClass
from models import file_ops_models as models
from models.base_models import APIResponse
from models.base_models import EAPIResponseCode
from resources.error_handler import catch_internal
from resources.helpers import get_files_recursive
from resources.helpers import get_resource_bygeid
from resources.helpers import location_decoder
from resources.redis import SrvAioRedisSingleton

router = APIRouter()


@cbv(router)
class FileOperationsValidate:
    def __init__(self):
        self._logger = LoggerFactory('api_file_operations_validate').get_logger()

    @router.post('/repeat-check', summary='File operations repeated check api, validate file operation job')
    @catch_internal('api_file_operations_validate')
    async def repeat_check(self, data: models.FileOperationsPOST):
        api_response = APIResponse()
        # permission control, operation lock
        # selete check worker
        job_dispatcher = {'copy': repeated_check}.get(data.operation, None)
        if not job_dispatcher:
            api_response.code = EAPIResponseCode.bad_request
            api_response.error_msg = 'Invalid operation'
            return api_response.json_response()
        code, result = await job_dispatcher(self._logger, data)
        api_response.code = code
        if not api_response.code == EAPIResponseCode.success:
            api_response.error_msg = 'Error occured'
        api_response.result = result
        return api_response.json_response()

    @router.post('/', summary='File operations api, validate file operation job')
    @catch_internal('api_file_operations_validate')
    async def post(self, data: models.FileOperationsValidatePOST):
        """flatten targets => find unique_path(ingestion path)

        => find destination_path(copy only) => validate operation => validate repeated => return results
        """
        api_response = APIResponse()
        srv_redis = SrvAioRedisSingleton()
        files_validation = []
        to_validate_files = []
        to_validate = []
        '''
        {
            'geid': optional,
            'full_path': ingestion_path
        }
        '''
        try:
            # validate project
            project_validation_code, validation_result = await validate_project(data.project_geid)
            if project_validation_code != EAPIResponseCode.success:
                return project_validation_code, validation_result
            project_info = validation_result
            targets = data.payload['targets']
            dest = data.payload.get('destination', None)
            # init validation
            for target in targets:
                if target.get('geid'):
                    source = await get_resource_bygeid(target['geid'])
                    if not source:
                        raise Exception('Not found resource: ' + target['geid'])
                    target['resource_type'] = get_resource_type(source['labels'])
                    source['resource_type'] = target['resource_type']
                    if not target['resource_type'] in ['File', 'Folder']:
                        api_response.error_msg = '[Fatal]Invalid target, target must be Folder or File: ' + str(target)
                        api_response.code = EAPIResponseCode.bad_request
                        return api_response
                    target['zone'] = get_zone(source['labels'])
                    source['zone'] = target['zone']
                    target['name'] = source['name']
                    if source['resource_type'] == 'File':
                        source['rename'] = target.get('rename')
                        to_validate_files.append(source)
                else:
                    to_validate.append({'full_path': target['full_path']})
            # flatten folders
            for target in targets:
                if target.get('resource_type') == 'Folder':
                    child_files = await get_files_recursive(target['geid'], [])
                    for source in child_files:
                        source['resource_type'] = 'File'
                        source['zone'] = get_zone(source['labels'])
                        source['target_folder_geid'] = target['geid']
                        source['source_folder_rename'] = target['rename'] if target.get('rename') else target['name']
                        to_validate_files.append(source)
            # generate validate objects
            to_validate += [
                {
                    'geid': node.get('target_folder_geid')
                    if 'target_folder_geid' in node
                    else node.get('global_entity_id'),
                    'full_path': get_ingestion_path(node),
                    'entity_geid': node.get('global_entity_id'),
                    'location': node.get('location'),
                    'source_folder': node.get('target_folder_geid'),
                    'source_folder_rename': node.get('source_folder_rename'),
                    'copy_name': node['rename'] if node.get('rename') else node['name'],
                }
                for node in to_validate_files
            ]
            # # copy validation temporary disabled
            # if data.operation == 'copy':
            #     api_response.code = EAPIResponseCode.success
            #     api_response.result = await copy_validation(project_info['code'],
            #         to_validate, dest, data.operation, srv_redis)
            #     return api_response
            # validate operation lock
            for target in to_validate:
                current_file_action = await srv_redis.file_get_status(target['full_path'])
                is_valid = validate_operation(data.operation, current_file_action)
                validation = {
                    'is_valid': is_valid,
                    'geid': target.get('geid', None),
                    'full_path': target['full_path'],
                    'current_file_action': current_file_action,
                }
                files_validation.append(validation)
                if not is_valid:
                    validation['error'] = 'operation-block'
                files_validation.sort(key=lambda v: v['is_valid'])
            api_response.result = files_validation
        except Exception as e:
            self._logger.info('Error in getting current action: ' + str(e))
            api_response.code = EAPIResponseCode.internal_error
            api_response.result = 'Error in getting current action: ' + str(e)
            return api_response
        return api_response


def get_resource_type(labels: list):
    """Get resource type by neo4j labels."""

    resources = ['File', 'TrashFile', 'Folder', 'Container']
    for label in labels:
        if label in resources:
            return label
    return None


def get_zone(labels: list):
    """Get zone by neo4j labels."""

    zones = [ConfigClass.GREEN_ZONE_LABEL, ConfigClass.CORE_ZONE_LABEL]
    for label in labels:
        if label in zones:
            return label
    return None


def get_ingestion_path(source: dict):
    location = source['location']
    ingestion_type, ingestion_host, ingestion_path = location_decoder(location)
    return ingestion_path
