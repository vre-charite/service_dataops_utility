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

import httpx
from fastapi import APIRouter
from fastapi_utils.cbv import cbv
from logger import LoggerFactory
from config import ConfigClass
from models.base_models import APIResponse
from models.base_models import EAPIResponseCode
from models.tags_models import SysTagsAPIPOST
from models.tags_models import TagsAPIPOST
from resources.error_handler import catch_internal
from resources.helpers import get_resource_bygeid
from resources.helpers import http_query_node
from resources.utils import get_resource_type
from resources.utils import update_elastic_search_entity
from resources.utils import validate_taglist

router = APIRouter()

_logger = LoggerFactory('api_tags').get_logger()
OPERATION_TERMINATED = 'terminated'
OPERATION_SUCCESS = 'success'
LIMIT_REACHED = 'limit_reached'


@cbv(router)
class TagsAPI:
    def __init__(self):
        self._logger = LoggerFactory('api_tags').get_logger()

    @router.post('/{entity_geid}/tags', summary='API to add / remove tags for an entity file/folder')
    @catch_internal('api_tags')
    async def post(self, entity_geid: str, entity_type: str, data: TagsAPIPOST):

        _res = APIResponse()
        data_tags = data.tags
        inherit = data.inherit
        final_res = []
        if not entity_geid or not isinstance(data_tags, list) or not isinstance(entity_geid, str):
            self._logger.error('Tags and geid are required')
            _res.code = EAPIResponseCode.bad_request
            _res.error_msg = 'tags and geid are required.'
            return _res.json_response()

        valid, validate_data = validate_taglist(data_tags, inherit)
        if not valid:
            self._logger.error(f"Invalid tags : {validate_data['error']}")
            _res.error_msg = f"Invalid tags : {validate_data['error']}"
            _res.code = EAPIResponseCode.bad_request
            return _res.json_response()
        try:
            # overwrite tags list of current folder
            self._logger.info('Fetch tags and entity_id from neo4j')
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    ConfigClass.NEO4J_SERVICE + f'nodes/{entity_type}/query', json={'global_entity_id': entity_geid}
                )
            if len(response.json()) == 0:
                self._logger.info(f'{entity_type} does not exist')
                _res.code = EAPIResponseCode.not_found
                _res.error_msg = f'{entity_type} does not exist'
                return _res.json_response()
            res = await update_tags(entity_geid=entity_geid, tags_list=data_tags, tag_type='tags')
            final_res.extend(res)
            # entity is folder and inherit is true, add new tags list to old tags of child nodes under "system_tags"
            if inherit and entity_type == 'Folder':
                child_tags_res = await update_tags_nested_entity(tag_type='tags', geid=entity_geid, tags=data_tags)
                final_res.extend(child_tags_res)
            final_res.append({'total': len(final_res)})
            _res.code = EAPIResponseCode.success
            _res.result = final_res
            return _res.json_response()
        except Exception as error:
            self._logger.error(f'Error while including tags : {error}')
            _res.code = EAPIResponseCode.internal_error
            _res.error_msg = f'Error while including tags : {error}'
            return _res.json_response(), _res.code


@cbv(router)
class SysTagsAPI:
    def __init__(self):
        self._logger = LoggerFactory('api_tags').get_logger()

    @router.post('/{entity_geid}/systags', summary='API to add / remove tags for an entity file/folder')
    @catch_internal('api_system_tags')
    async def post(self, entity_geid: str, entity_type: str, data: SysTagsAPIPOST):

        _res = APIResponse()
        systags = data.systags
        inherit = data.inherit
        final_res = []
        valid, validate_data = validate_taglist(systags, inherit)
        if not valid:
            # validate_data = validate_data.json()
            self._logger.error(f"Invalid tags : {validate_data['error']}")
            _res.error_msg = f"Invalid tags : {validate_data['error']}"
            _res.code = EAPIResponseCode.bad_request
            return _res.json_response()

        # Fetch entity from neo4j
        response = await http_query_node(entity_type, entity_geid)
        if not response.json():
            self._logger.error(f'{entity_type} not found')
            _res.code = EAPIResponseCode.not_found
            _res.error_msg = f'{entity_type} not found'
            return _res.json_response()

        # append new tags to list of tags of current entity
        async with httpx.AsyncClient() as client:
            response = await client.post(
                ConfigClass.NEO4J_SERVICE + f'nodes/{entity_type}/query', json={'global_entity_id': entity_geid}
            )

        entity_details = response.json()[0]
        try:
            tags_list = entity_details.get('system_tags', [])
            updated_list = systags + tags_list
            tags_list = list(dict.fromkeys(updated_list))
            # tags_list.extend(systags)
            # tags_list = list(dict.fromkeys(tags_list))
        except KeyError as error:
            self._logger.error(f'No system tags found for entity : {error}')
            tags_list = systags
        res = await update_tags(entity_geid=entity_geid, tags_list=tags_list, tag_type='system_tags')
        final_res.extend(res)
        # entity is folder and inherit is true, add new tags list to old tags of child nodes under "system_tags"
        if inherit and entity_type == 'Folder':
            child_tags_res = await update_tags_nested_entity(tag_type='system_tags', geid=entity_geid, tags=systags)
            final_res.extend(child_tags_res)
        final_res.append({'total': len(final_res)})
        _res.code = EAPIResponseCode.success
        _res.result = final_res
        return _res.json_response()


async def http_neo4j_update_tags(entity, entity_id, tags_list, tag_type):
    _logger.info('Update tags for the given entity')
    payload = {tag_type: tags_list}
    async with httpx.AsyncClient() as client:
        res = await client.put(ConfigClass.NEO4J_SERVICE + f'nodes/{entity}/node/{entity_id}', json=payload)
    return res.json()


async def update_tags_nested_entity(geid, tags, tag_type):
    async with httpx.AsyncClient() as client:
        response = await client.get(ConfigClass.NEO4J_SERVICE + f'relations/connected/{geid}?direction=output')
    api_res = []
    if not len(response.json()['result']) == 0:
        data = response.json()['result']
        for child in data:
            child_geid = child['global_entity_id']
            child_tags = child.get(tag_type, [])
            entity_type = get_resource_type(child['labels'])
            _logger.info(f'Adding new list of tags to given entity {child_geid}')
            updated_list = tags + child_tags
            # tags_list = list(dict.fromkeys(updated_list))
            # tags.extend(child_tags)
            # tags_list = list(dict.fromkeys(tags))
            res = await update_tags(entity_geid=child['global_entity_id'], tags_list=updated_list, tag_type=tag_type)
            api_res.extend(res)
            if entity_type == 'File':
                await update_elastic_search_entity(geid=child['global_entity_id'], taglist=updated_list, tag_type=tag_type)
    return api_res


async def update_tags(entity_geid, tags_list, tag_type):
    final_res = []
    entity_details = await get_resource_bygeid(entity_geid)
    entity_type = get_resource_type(entity_details['labels'])
    entity_id = entity_details['id']
    try:
        entity_tags = entity_details.get(tag_type, [])
    except KeyError:
        entity_tags = []
        _logger.error('No tags for the entity')

    entity_geid = entity_details.get("global_entity_id")
    display_path = entity_details.get("display_path", "")
    updated_tags = list(dict.fromkeys(tags_list))
    if len(updated_tags) > 10:
        current_entity_res = {
            'name': entity_details.get("name"),
            'geid': entity_geid,
            'display_path': display_path,
            tag_type: entity_tags,
            'operation_status': OPERATION_TERMINATED,
            'error_type': LIMIT_REACHED,
        }
        final_res.append(current_entity_res)
    else:
        _logger.info(f'Updating tag list for entity {entity_geid}')
        # tags_list = [tag for tag in entity_tags if tag not in tags]
        neo4j_res = await http_neo4j_update_tags(entity_type, entity_id=entity_id, tags_list=updated_tags, tag_type=tag_type)
        current_entity_res = {
            'name': entity_details['name'],
            'geid': entity_details['global_entity_id'],
            'display_path': display_path,
            tag_type: neo4j_res[0][tag_type],
            'operation_status': OPERATION_SUCCESS,
            'error_type': None,
        }
        await update_elastic_search_entity(geid=entity_details['global_entity_id'], taglist=updated_tags, tag_type=tag_type)
        final_res.append(current_entity_res)
    return final_res
