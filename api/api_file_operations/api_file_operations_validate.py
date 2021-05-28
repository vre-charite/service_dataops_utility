import os
from config import ConfigClass
from resources.error_handler import catch_internal
from resources.helpers import get_resource_bygeid, get_files_recursive
from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from models.base_models import EAPIResponseCode, APIResponse
from models import file_ops_models as models
from resources.cataloguing_manager import CataLoguingManager
from commons.logger_services.logger_factory_service import SrvLoggerFactory
from commons.data_providers.redis import SrvRedisSingleton
from .validations import validate_operation, validate_project, validate_destination_repeated
from .copy_dispatcher import get_copy_destination_path

router = APIRouter()


@cbv(router)
class FileOperationsValidate:
    def __init__(self):
        self._logger = SrvLoggerFactory(
            'api_file_operations_validate').get_logger()

    @router.post('/',  summary="File operations api, validate file operation job")
    @catch_internal('api_file_operations_validate')
    async def post(self, data: models.FileOperationsValidatePOST):
        api_response = APIResponse()

        srv_redis = SrvRedisSingleton()

        files_validation = []

        try:
            # validate project
            project_validation_code, validation_result = validate_project(
                data.project_geid)
            if project_validation_code != EAPIResponseCode.success:
                return project_validation_code, validation_result
            project_info = validation_result

            # find full_path in neo4j db
            targets_files = data.payload['targets']
            dest = data.payload.get('destination', None)
            # init validation
            for target in targets_files:
                if target.get("geid"):
                    source = get_resource_bygeid(target["geid"])
                    target['resource_type'] = get_resource_type(
                        source['labels'])
                    source['resource_type'] = target['resource_type']
                    if not target['resource_type'] in ['File', 'Folder']:
                        api_response.error_msg = '[Fatal]Invalid target, target must be Folder or File: ' + str(
                            target)
                        api_response.code = EAPIResponseCode.bad_request
                        return api_response
                    target['zone'] = get_zone(source['labels'])
                    source['zone'] = target['zone']
                    target['name'] = source['name']
                    target['full_path'] = get_full_path(source, project_info['code'])

            # copy validation
            if data.operation == 'copy':
                api_response.code = EAPIResponseCode.success
                api_response.result = copy_validation(project_info['code'], targets_files, dest, data.operation, srv_redis)
                return api_response

            # get child files
            child_file_nodes = []
            for target in targets_files:
                if target['resource_type'] == 'Folder':
                    child_files = get_files_recursive(target['geid'], [])
                    for source in child_files:
                        child_file_nodes.append({
                            'name': source['name'],
                            'geid': source['global_entity_id'],
                            'full_path': source['full_path'],
                            'zone': get_zone(source['labels']),
                            'resource_type': 'File'
                        })
            targets_files += child_file_nodes
            # target_file include folders and files
            # validate operation lock
            for target in targets_files:
                current_file_action = srv_redis.file_get_status(
                    target['full_path'])

                is_valid = validate_operation(
                    data.operation, current_file_action)
                validation = {
                    "is_valid": is_valid,
                    "geid": target['geid'],
                    "full_path": target['full_path'],
                    "current_file_action": current_file_action
                }
                files_validation.append(validation)
                if not is_valid:
                    validation['error'] = 'operation-block'

            api_response.result = files_validation

        except Exception as e:
            self._logger.info('Error in getting current action: ' + str(e))
            api_response.code = EAPIResponseCode.internal_error
            api_response.result = 'Error in getting current action: ' + str(e)
            return api_response

        return api_response


def copy_validation(project_code, targets, destination_geid, operation, srv_redis):
    validations = []
    # validate operation lock
    for target in targets:
        current_file_action = srv_redis.file_get_status(
            target['full_path'])

        is_valid = validate_operation(
            operation, current_file_action)
        validation = {
            "is_valid": is_valid,
            "geid": target['geid'],
            "full_path": target['full_path'],
            "current_file_action": current_file_action
        }
        validations.append(validation)
        if not is_valid:
            validation['error'] = 'operation-block'
    # check copy destination
    for target in targets:
        copied_name = target.get("rename", target['name'])
        destination_path = get_copy_destination_path(
            project_code, copied_name, destination_geid)
        is_valid, found = validate_destination_repeated(
            "VRECore", project_code, target['resource_type'], destination_path)
        validation = [
            validation for validation in validations if validation['geid'] == target['geid']][0]
        validation['destination_path'] = destination_path
        if not is_valid:
            validation['error'] = 'entity-exist'
            validation['is_valid'] = is_valid
            validation['found'] = found['global_entity_id']
            validation['found_name'] = found['name'] 
    return validations


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
