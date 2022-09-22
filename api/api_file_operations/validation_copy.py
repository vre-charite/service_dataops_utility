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

import asyncio
import os

from api.api_file_operations.validations import validate_file_repeated
from api.api_file_operations.validations import validate_folder_repeated
from api.api_file_operations.validations import validate_operation
from api.api_file_operations.validations import validate_project
from models import file_ops_models as models
from models.base_models import EAPIResponseCode
from resources.helpers import get_connected_nodes
from resources.helpers import get_resource_bygeid
from resources.helpers import location_decoder
from config import ConfigClass


async def copy_validation(project_code, to_validate, destination_geid, operation, srv_redis):
    validations = []
    # validate operation lock
    await asyncio.wait([copy_thread(destination_geid, project_code, node,
                                    operation, srv_redis, validations) for node in to_validate])
    validations.sort(key=lambda v: v['is_valid'])
    return validations


async def copy_thread(destination_geid, project_code, node,
                      operation, srv_redis, validations):
    location = node['location']
    ingestion_type, ingestion_host, ingestion_path = location_decoder(
        location)
    # get destination
    destination = None
    if destination_geid:
        destination_folder = await get_resource_bygeid(destination_geid)
        if not destination_folder:
            raise Exception('Not found resource: ' + destination_geid)
        destination_folder['resource_type'] = get_resource_type(
            destination_folder['labels'])
        if not destination_folder['resource_type'] in ['Folder', 'Container']:
            raise Exception(
                'Invalid destination, must be a folder or project.')
        if destination_folder['resource_type'] == 'Folder':
            destination = destination_folder
    # generate meta info for destination
    bucket_name = 'core-{}'.format(project_code)
    destination_prefix = os.path.join(bucket_name, destination['folder_relative_path'], destination['name'])
    destination_file_node = {
        'full_path': '',
        'geid': node['geid']
    }
    # get relative path to source folder
    source_folder = node.get('source_folder')
    if source_folder:
        input_nodes = await get_connected_nodes(
            node["entity_geid"], "input")
        input_nodes = [
            node for node in input_nodes if 'Folder' in node['labels']]
        input_nodes.sort(key=lambda f: f['folder_level'])
        found_source_node = [
            input_node for input_node in input_nodes if input_node['global_entity_id'] == source_folder][0]
        path_relative_to_source_path = ''
        source_index = input_nodes.index(found_source_node)
        folder_name_list = [node['name']
                            for node in input_nodes[source_index + 1:]]
        path_relative_to_source_path = os.sep.join(folder_name_list)
        output_folder_name = node.get('source_folder_rename')
        node['path_relative_to_source_path'] = path_relative_to_source_path
        node['ouput_relative_path'] = os.path.join(
            output_folder_name, path_relative_to_source_path)
        destination_file_node['full_path'] = os.path.join(
            destination_prefix, node['ouput_relative_path'], node['copy_name'])
    else:
        destination_file_node['full_path'] = os.path.join(
            destination_prefix, node['copy_name'])
    # check target file
    current_file_action = await srv_redis.file_get_status(
        node['full_path'])
    is_valid = validate_operation(
        operation, current_file_action)
    validation = {
        "is_valid": is_valid,
        "geid": node['geid'],
        "full_path": node['full_path'],
        "current_file_action": current_file_action
    }
    validations.append(validation)
    if not is_valid:
        validation['error'] = 'operation-block'

    # check destination file
    dest_file_action = await srv_redis.file_get_status(
        destination_file_node['full_path'])
    is_valid = validate_operation(
        operation, dest_file_action)
    dest_validation = {
        "is_valid": is_valid,
        "geid": destination_file_node['geid'],
        "full_path": destination_file_node['full_path'],
        "current_file_action": dest_file_action
    }
    validations.append(dest_validation)
    if not is_valid:
        dest_validation['error'] = 'operation-block'
    # check copy destination repeated
    dest_location = "{}://{}/{}".format(ingestion_type, ingestion_host, destination_file_node['full_path'])
    is_valid, found = await validate_file_repeated(
        ConfigClass.CORE_ZONE_LABEL, project_code, dest_location)
    if not is_valid:
        dest_validation['error'] = 'entity-exist'
        dest_validation['is_valid'] = is_valid
        dest_validation['found'] = found['global_entity_id']
        dest_validation['found_name'] = found['name']


async def repeated_check(_logger, data: models.FileOperationsPOST):
    '''
    return tuple response_code, worker_result
    '''
    # validate project
    project_validation_code, validation_result = await validate_project(
        data.project_geid)
    if project_validation_code != EAPIResponseCode.success:
        return project_validation_code, validation_result
    project_info = validation_result
    project_code = validation_result.get("code", None)

    payload = data.payload.dict()

    # validate destination
    destination_geid = payload.get('destination', None)
    node_destination = None
    if destination_geid:
        node_destination = await get_resource_bygeid(destination_geid)
        if not node_destination:
            raise Exception('Not found resource: ' + destination_geid)
        node_destination['resource_type'] = get_resource_type(
            node_destination['labels'])
        if not node_destination['resource_type'] in ['Folder', 'Container']:
            return EAPIResponseCode.bad_request, "Invalid destination type: " + destination_geid

    # validate targets
    targets = payload["targets"]
    to_validate_repeat_geids = []
    repeated = []

    async def validate_targets(targets: list):
        fetched = []
        try:
            for target in targets:
                # get source file
                source = await get_resource_bygeid(target['geid'])
                if not source:
                    raise Exception('Not found resource: ' + target['geid'])
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

    validated, validation_result = await validate_targets(targets)
    if not validated:
        return EAPIResponseCode.bad_request, validation_result

    sources = validation_result

    flattened_sources = [
        node for node in sources if node['resource_type'] == "File"]
    # flatten sources
    for source in sources:
        # append path and attrs
        if source["resource_type"] == "Folder":
            nodes_child = await get_connected_nodes(
                source['global_entity_id'], "output")
            nodes_child_files = [
                node for node in nodes_child if "File" in node["labels"]]

            # check folder repeated
            target_folder_relative_path = ""
            if node_destination and node_destination['resource_type'] == 'Folder':
                target_folder_relative_path = os.path.join(
                    node_destination['folder_relative_path'], node_destination['name'])
            output_folder_name = source.get('rename', source['name'])
            is_valid, found = await validate_folder_repeated(
                ConfigClass.CORE_ZONE_LABEL, project_code, target_folder_relative_path, output_folder_name)
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
                input_nodes = await get_connected_nodes(
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
            is_valid, found = await validate_file_repeated(
                ConfigClass.CORE_ZONE_LABEL, project_code, dest_location)
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

    return EAPIResponseCode.success, []


def get_resource_type(labels: list):
    '''
    Get resource type by neo4j labels
    '''
    resources = ['File', 'TrashFile', 'Folder', 'Container']
    for label in labels:
        if label in resources:
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
