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

import re
from typing import Optional

import httpx
from common import GEIDClient

from config import ConfigClass


def fetch_geid():
    client = GEIDClient()
    geid = client.get_GEID()
    return geid


async def get_resource_bygeid(geid: str) -> Optional[dict]:
    """Get the node by geid.

    raise exception if the geid does not exist.
    """
    url = f'{ConfigClass.NEO4J_SERVICE}nodes/geid/{geid}'
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
    nodes = res.json()

    if len(nodes) == 0:
        raise Exception('Not found resource: ' + geid)

    return nodes[0]


async def get_files_recursive(folder_geid, all_files=None):
    if all_files is None:
        all_files = []

    query = {
        'start_label': 'Folder',
        'end_labels': ['File', 'Folder'],
        'query': {
            'start_params': {
                'global_entity_id': folder_geid,
            },
            'end_params': {},
        },
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(ConfigClass.NEO4J_SERVICE_V2 + 'relations/query', json=query)
    for node in resp.json()['results']:
        if 'File' in node['labels']:
            all_files.append(node)
        else:
            await get_files_recursive(node['global_entity_id'], all_files=all_files)
    return all_files


def get_resource_type(labels: list):
    """Get resource type by neo4j labels."""
    resources = ['File', 'TrashFile', 'Folder', 'Container']
    for label in labels:
        if label in resources:
            return label
    return None


async def get_connected_nodes(geid, direction: str = 'both'):
    """return a list of nodes."""
    if direction == 'both':
        params = {'direction': 'input'}
        url = ConfigClass.NEO4J_SERVICE + 'relations/connected/{}'.format(geid)
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
        if response.status_code != 200:
            raise Exception(
                'Internal error for neo4j service, \
                when get_connected, geid: '
                + str(geid)
            )
        connected_nodes = response.json()['result']
        params = {'direction': 'output'}
        url = ConfigClass.NEO4J_SERVICE + 'relations/connected/{}'.format(geid)
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
        if response.status_code != 200:
            raise Exception(
                'Internal error for neo4j service, \
                when get_connected, geid: '
                + str(geid)
            )
        return connected_nodes + response.json()['result']
    params = {'direction': direction}
    url = ConfigClass.NEO4J_SERVICE + 'relations/connected/{}'.format(geid)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
    if response.status_code != 200:
        raise Exception(
            'Internal error for neo4j service, \
            when get_connected, geid: '
            + str(geid)
        )
    connected_nodes = response.json()['result']
    return connected_nodes


def location_decoder(location: str):
    """decode resource location return ingestion_type, ingestion_host, ingestion_path."""
    splits_loaction = location.split('://', 1)
    ingestion_type = splits_loaction[0]
    ingestion_url = splits_loaction[1]
    path_splits = re.split(r'(?<!/)/(?!/)', ingestion_url, 1)
    ingestion_host = path_splits[0]
    ingestion_path = path_splits[1]
    return ingestion_type, ingestion_host, ingestion_path


async def http_query_node(primary_label, query_params={}):
    """primary_label i.e. Folder, File, Container."""
    payload = {**query_params}
    node_query_url = ConfigClass.NEO4J_SERVICE + 'nodes/{}/query'.format(primary_label)
    async with httpx.AsyncClient() as client:
        response = await client.post(node_query_url, json=payload)
    return response
