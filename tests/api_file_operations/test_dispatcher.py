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

import random
import time
import uuid
from typing import Any
from typing import Callable

import pytest

from api.api_file_operations.dispatcher import Node
from api.api_file_operations.dispatcher import NodeList
from api.api_file_operations.dispatcher import ResourceType


def get_timestamp() -> int:
    """Return current timestamp."""

    return round(time.time())


@pytest.fixture
def create_node(fake) -> Callable[..., Node]:
    def _create_node(
        global_entity_id=None,
        name=None,
        resource_type=None,
        **kwds: Any,
    ) -> Node:
        if global_entity_id is None:
            global_entity_id = f'{uuid.uuid4()}-{get_timestamp()}'

        if name is None:
            name = fake.word()

        if resource_type is None:
            resource_type = random.choice(list(ResourceType))

        return Node(
            {
                'global_entity_id': global_entity_id,
                'name': name,
                'resource_type': resource_type,
                **kwds,
            }
        )

    return _create_node


class TestNode:
    def test_geid_returns_node_global_entity_id(self, create_node):
        node = create_node()
        expected_geid = node['global_entity_id']

        assert node.geid == expected_geid

    def test_name_returns_node_name(self, create_node):
        node = create_node()
        expected_name = node['name']

        assert node.name == expected_name


class TestNodeList:
    def test_new_instance_converts_list_values_into_source_instances(self):
        nodes = NodeList([{'key': 'value'}])

        assert isinstance(nodes[0], Node)

    def test_geids_returns_set_with_all_node_geids(self, create_node):
        node_1 = create_node()
        node_2 = create_node()
        nodes = NodeList([node_1, node_2])
        expected_geids = {node_1.geid, node_2.geid}

        assert expected_geids == nodes.geids

    def test_names_returns_list_with_all_node_names(self, create_node):
        node_1 = create_node()
        node_2 = create_node()
        nodes = NodeList([node_1, node_2])
        expected_names = [node_1.name, node_2.name]

        assert expected_names == nodes.names

    def test_filter_folders_returns_sources_with_folder_resource_type(self, create_node):
        expected_node = create_node(resource_type=ResourceType.FOLDER)

        sources = NodeList([create_node(resource_type=ResourceType.FILE), expected_node])

        assert sources.filter_folders() == [expected_node]

    def test_filter_files_returns_sources_with_file_resource_type(self, create_node):
        expected_node = create_node(resource_type=ResourceType.FILE)

        sources = NodeList([create_node(resource_type=ResourceType.FOLDER), expected_node])

        assert sources.filter_files() == [expected_node]
