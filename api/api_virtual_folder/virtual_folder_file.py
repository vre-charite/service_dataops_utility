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
from config import ConfigClass
from models import virtual_folder_models as models
from models.base_models import EAPIResponseCode

router = APIRouter()


@cbv(router)
class VirtualFolderFile:
    @router.delete(
        '/{collection_geid}', response_model=models.VirtualFolderFileDELETEResponse, summary='Delete a vfolder'
    )
    async def delete(self, collection_geid):
        api_response = models.VirtualFolderFileDELETEResponse()

        url = ConfigClass.NEO4J_SERVICE + f'nodes/VirtualFolder/query'
        payload = {'global_entity_id': collection_geid}
        async with httpx.AsyncClient() as client:
            result = await client.post(url, json=payload)
        if result.status_code != 200:
            api_response.error_msg = 'update vfolder in neo4j Error: ' + str(result.json())
            api_response.code = EAPIResponseCode.internal_error
            return api_response.json_response()
        vfolder_node = result.json()[0]
        vfolder_id = vfolder_node['id']

        url = ConfigClass.NEO4J_SERVICE + f'nodes/VirtualFolder/node/{vfolder_id}'
        async with httpx.AsyncClient() as client:
            result = await client.delete(url)
        if result.status_code != 200:
            api_response.code = EAPIResponseCode.internal_error
            api_response.error_msg = 'VirtualFolderFileDELETEResponse Error: ' + result.json()
            return api_response.json_response()
        api_response.result = 'success'
        return api_response.json_response()


@cbv(router)
class FileBulk:
    @router.post(
        '/{collection_geid}/files', response_model=models.VirtualFileBulkPOSTResponse, summary='Add files to vfolder'
    )
    async def post(self, collection_geid, data: models.VirtualFileBulkPOST):
        api_response = models.VirtualFileBulkPOSTResponse()
        file_geids = data.file_geids

        # Get vfolder
        url = ConfigClass.NEO4J_SERVICE + f'nodes/VirtualFolder/query'
        payload = {
            'global_entity_id': collection_geid,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
        if response.status_code != 200:
            api_response.code = response.status_code
            api_response.error_msg = response.json()
            return api_response.json_response()
        vfolder = response.json()[0]

        # Get folders dataset
        container_id = vfolder['container_id']
        url = ConfigClass.NEO4J_SERVICE + f'nodes/Container/node/{container_id}'
        async with httpx.AsyncClient() as client:
            result = await client.get(url)
        if result.status_code != 200:
            api_response.code = EAPIResponseCode.internal_error
            api_response.error_msg = 'Get folders dataset Error: ' + result.json()
            return api_response.json_response()
        if len(result.json()) < 1:
            api_response.code = EAPIResponseCode.not_found
            api_response.error_msg = 'Project not found'
            return api_response.json_response()

        dataset = result.json()[0]

        duplicate = False
        for geid in file_geids:
            # Duplicate check
            url = ConfigClass.NEO4J_SERVICE_V2 + f'relations/query'
            payload = {
                'start_label': 'VirtualFolder',
                'end_labels': ['File', 'Folder'],
                'query': {
                    'start_params': {
                        'global_entity_id': vfolder['global_entity_id'],
                    },
                    'end_params': {
                        'File': {
                            'global_entity_id': geid,
                        },
                        'Folder': {
                            'global_entity_id': geid,
                        },
                    },
                },
            }
            async with httpx.AsyncClient() as client:
                result = await client.post(url, json=payload)
            if result.status_code != 200:
                api_response.code = EAPIResponseCode.internal_error
                api_response.error_msg = 'Duplicate check Error: ' + result.json()
                return api_response.json_response()

            if len(result.json()['results']) > 0:
                duplicate = True
                continue

            # Get file from neo4j
            payload = {
                'global_entity_id': geid,
            }
            try:
                async with httpx.AsyncClient() as client:
                    result = await client.post(ConfigClass.NEO4J_SERVICE + f'nodes/File/query', json=payload)
                result = result.json()[0]
            except Exception:
                async with httpx.AsyncClient() as client:
                    result = await client.post(ConfigClass.NEO4J_SERVICE + f'nodes/Folder/query', json=payload)
                result = result.json()[0]

            if not result:
                api_response.code = EAPIResponseCode.not_found
                api_response.error_msg = 'File not found in neo4j'
                return api_response.json_response()

            # Check to make sure it's a core file
            if not ConfigClass.CORE_ZONE_LABEL in result['labels']:
                api_response.code = EAPIResponseCode.forbidden
                api_response.error_msg = 'Permission denied'
                return api_response.json_response()

            if result['project_code'] != dataset['code']:
                api_response.code = EAPIResponseCode.forbidden
                api_response.error_msg = 'File does not belong to project'
                return api_response.json_response()

            # Add folder relation to file
            url = ConfigClass.NEO4J_SERVICE + f'relations/contains'
            payload = {
                'start_id': vfolder['id'],
                'end_id': result['id'],
            }
            async with httpx.AsyncClient() as client:
                result = await client.post(url, json=payload)
            if result.status_code != 200:
                api_response.code = EAPIResponseCode.internal_error
                api_response.error_msg = 'Add folder relation to file Error: ' + result.json()
                return api_response.json_response()

        if duplicate:
            api_response.result = 'duplicate'
        else:
            api_response.result = 'success'
        return api_response.json_response()

    @router.delete(
        '/{collection_geid}/files',
        response_model=models.VirtualFileBulkDELETEResponse,
        summary='Remove file from folder',
    )
    async def delete(self, collection_geid, data: models.VirtualFileBulkDELETE):
        api_response = models.VirtualFileBulkDELETEResponse()
        file_geids = data.file_geids

        for geid in file_geids:
            # Get vfolder
            url = ConfigClass.NEO4J_SERVICE + f'nodes/VirtualFolder/query'
            payload = {
                'global_entity_id': collection_geid,
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload)
            if response.status_code != 200:
                api_response.code = response.status_code
                api_response.error_msg = response.json()
                return api_response.json_response()
            if not response.json():
                api_response.code = EAPIResponseCode.not_found
                api_response.error_msg = 'Virtual Folder not found'
                return api_response.json_response()
            folder_id = response.json()[0]['id']

            # Get file
            url = ConfigClass.NEO4J_SERVICE_V2 + f'relations/query'
            payload = {
                'start_label': 'VirtualFolder',
                'end_labels': ['File', 'Folder'],
                'query': {
                    'start_params': {
                        'global_entity_id': collection_geid,
                    },
                    'end_params': {
                        'File': {
                            'global_entity_id': geid,
                        },
                        'Folder': {
                            'global_entity_id': geid,
                        },
                    },
                },
            }
            async with httpx.AsyncClient() as client:
                result = await client.post(url, json=payload)
            if result.status_code != 200:
                api_response.code = EAPIResponseCode.internal_error
                api_response.error_msg = 'Get file Error: ' + result.json()
                return api_response.json_response()
            result = result.json()['results']
            if len(result) > 1:
                api_response.code = EAPIResponseCode.internal_error
                api_response.error_msg = 'multiple files, aborting'
                return api_response.json_response()
            if not result:
                api_response.code = EAPIResponseCode.not_found
                api_response.error_msg = 'File not found'
                return api_response.json_response()
            file_id = result[0]['id']

            # Remove relationship from neo4j
            relation_query = {
                'start_id': int(folder_id),
                'end_id': file_id,
            }
            async with httpx.AsyncClient() as client:
                result = await client.delete(ConfigClass.NEO4J_SERVICE + 'relations', params=relation_query)
            if result.status_code != 200:
                api_response.code = EAPIResponseCode.internal_error
                api_response.error_msg = 'Remove relationship from neo4j Error: ' + result.json()
                return api_response.json_response()
        api_response.result = 'success'
        return api_response.json_response()
