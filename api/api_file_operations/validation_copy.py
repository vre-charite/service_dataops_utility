import os
import asyncio
from resources.helpers import get_resource_bygeid, location_decoder, \
    get_connected_nodes
from .validations import validate_operation, validate_file_repeated

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
        destination_folder = get_resource_bygeid(destination_geid)
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
        input_nodes = get_connected_nodes(
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
    current_file_action = srv_redis.file_get_status(
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
    dest_file_action = srv_redis.file_get_status(
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
    is_valid, found = validate_file_repeated(
        "VRECore", project_code, dest_location)
    if not is_valid:
        dest_validation['error'] = 'entity-exist'
        dest_validation['is_valid'] = is_valid
        dest_validation['found'] = found['global_entity_id']
        dest_validation['found_name'] = found['name']


def get_resource_type(labels: list):
    '''
    Get resource type by neo4j labels
    '''
    resources = ['File', 'TrashFile', 'Folder', 'Container']
    for label in labels:
        if label in resources:
            return label
    return None