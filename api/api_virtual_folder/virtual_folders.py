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

import copy
import httpx
from fastapi import APIRouter
from fastapi_utils.cbv import cbv
from config import ConfigClass
from models import virtual_folder_models as models
from models.base_models import APIResponse
from models.base_models import EAPIResponseCode
from resources.helpers import fetch_geid

router = APIRouter()


@cbv(router)
class VirtualFolder:
    @router.get('/', response_model=models.VirtualFolderGETResponse, summary='Get the collection belonging to user')
    async def get(self, project_geid: str, username: str):
        api_response = APIResponse()
        container_id = await self.get_container_id(project_geid)
        if container_id is None:
            api_response.code = EAPIResponseCode.not_found
            api_response.error_msg = 'Project not found'
            return api_response.json_response()

        # Get folder
        url = ConfigClass.NEO4J_SERVICE + 'nodes/VirtualFolder/query'
        payload = {'owner': username, 'container_id': container_id}
        async with httpx.AsyncClient() as client:
            result = await client.post(url, json=payload)

        if result.status_code != 200:
            api_response.code = result.status_code
            api_response.error_msg = 'Get folder error'
            return api_response.json_response()
        result = result.json()
        folders = []
        for node in result:
            folders.append(
                {
                    'global_entity_id': node['global_entity_id'],
                    'labels': node['labels'],
                    'properties': {
                        'name': node['name'],
                        'time_created': node['time_created'],
                        'time_lastmodified': node['time_lastmodified'],
                        'project_geid': node['global_entity_id'],
                    },
                }
            )
        api_response.result = folders
        return api_response.json_response()

    @router.post('/', response_model=models.VirtualFolderPOSTResponse, summary='Create a collection')
    async def post(self, data: models.VirtualFolderPOST):
        api_response = models.VirtualFolderPOSTResponse()
        folder_name = data.name
        project_geid = data.project_geid
        username = data.username
        # add internal func
        container_id = await self.get_container_id(project_geid)
        if container_id is None:
            api_response.code = EAPIResponseCode.not_found
            api_response.error_msg = 'Project not found'
            return api_response.json_response()

        # Folder count check
        url = ConfigClass.NEO4J_SERVICE + 'nodes/VirtualFolder/query'
        payload = {
            'owner': username,
            'container_id': int(container_id),
        }
        async with httpx.AsyncClient() as client:
            result = await client.post(url, json=payload)
        result = result.json()
        if len(result) >= 10:
            api_response.error_msg = 'Folder limit reached'
            api_response.code = EAPIResponseCode.bad_request
            return api_response.json_response()

        # duplicate check
        url = ConfigClass.NEO4J_SERVICE + 'nodes/VirtualFolder/query'
        payload = {'owner': username, 'container_id': int(container_id), 'name': folder_name}
        async with httpx.AsyncClient() as client:
            result = await client.post(url, json=payload)
        result = result.json()
        if len(result) > 0:
            api_response.error_msg = 'Found duplicate folder'
            api_response.code = EAPIResponseCode.conflict
            return api_response.json_response()

        # Create vfolder in neo4j
        url = ConfigClass.NEO4J_SERVICE + 'nodes/VirtualFolder'
        payload = {
            'name': folder_name,
            'container_id': container_id,
            'global_entity_id': fetch_geid(),
            'owner': username,
        }
        async with httpx.AsyncClient() as client:
            result = await client.post(url, json=payload)
        if result.status_code != 200:
            api_response.error_msg = 'Create vfolder in neo4j:' + result.json()
            api_response.code = EAPIResponseCode.internal_error
            return api_response.json_response()
        vfolder_result = result.json()[0]
        vfolder = copy.deepcopy(vfolder_result)
        api_response.result = vfolder

        del vfolder['id']
        del vfolder['container_id']
        vfolder['project_geid'] = project_geid
        return api_response.json_response()

    @router.put('/', response_model=models.VirtualFolderPUTResponse, summary='Bulk update virtual folders')
    async def put(self, data: models.VirtualFolderPUT):
        api_response = models.VirtualFolderPOSTResponse()
        username = data.username
        results = []
        update_name = set()
        for collection in data.collections:
            # check required attributes
            for attr in ['name', 'geid']:
                if not collection.get(attr):
                    api_response.error_msg = f'Missing required attribute {attr}'
                    api_response.code = EAPIResponseCode.bad_request
                    return api_response.json_response()
            update_name.add(collection['name'])
        # Check duplicate name in payload
        if len(update_name) != len(data.collections):
            api_response.error_msg = 'Duplicate update collection names'
            api_response.code = EAPIResponseCode.bad_request
            return api_response.json_response()

        for vfolder in data.collections:
            # Get vfolder by geid
            url = f'{ConfigClass.NEO4J_SERVICE}nodes/VirtualFolder/query'
            payload = {
                'global_entity_id': vfolder['geid'],
                'owner': username,
            }
            async with httpx.AsyncClient() as client:
                result = await client.post(url, json=payload)

            if len(result.json()) < 1:
                api_response.code = EAPIResponseCode.forbidden
                api_response.error_msg = 'Permission Denied'
                return api_response.json_response()

            if result.status_code != 200:
                api_response.error_msg = 'Neo4j Error: ' + result.json()
                api_response.code = EAPIResponseCode.internal_error
                return api_response.json_response()
            vfolder_node = result.json()[0]
            folder_id = vfolder_node['id']
            container_id = vfolder_node['container_id']

            # duplicate check
            url = ConfigClass.NEO4J_SERVICE + 'nodes/VirtualFolder/query'
            payload = {'owner': username, 'container_id': container_id, 'name': vfolder['name']}
            async with httpx.AsyncClient() as client:
                result = await client.post(url, json=payload)
            result = result.json()
            if len(result) > 0:
                api_response.error_msg = 'Found duplicate folder'
                api_response.code = EAPIResponseCode.conflict
                return api_response.json_response()

            # update vfolder in neo4j
            url = ConfigClass.NEO4J_SERVICE + f'nodes/VirtualFolder/node/{folder_id}'
            payload = {
                'name': vfolder['name'],
            }
            async with httpx.AsyncClient() as client:
                result = await client.put(url, json=payload)
            if result.status_code != 200:
                api_response.error_msg = 'Neo4j Error: ' + result.json()
                api_response.code = EAPIResponseCode.internal_error
                return api_response.json_response()
            vfolder = result.json()[0]

            # get container
            url = ConfigClass.NEO4J_SERVICE + f'nodes/Container/node/{container_id}'
            async with httpx.AsyncClient() as client:
                result = await client.get(url)
            if result.status_code != 200:
                api_response.error_msg = 'Neo4j Error: ' + result.json()
                api_response.code = EAPIResponseCode.internal_error
                return api_response.json_response()
            project_geid = result.json()[0]['global_entity_id']

            del vfolder['id']
            del vfolder['container_id']
            vfolder['project_geid'] = project_geid
            results.append(vfolder)
        api_response.result = results
        return api_response.json_response()

    async def get_container_id(self, project_geid):
        url = f'{ConfigClass.NEO4J_SERVICE}nodes/Container/query'
        payload = {'global_entity_id': project_geid}
        async with httpx.AsyncClient() as client:
            result = await client.post(url, json=payload)
        if result.status_code != 200 or result.json() == []:
            return None
        result = result.json()[0]
        container_id = result['id']
        return container_id
