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

from enum import Enum
from enum import unique
from typing import Any
from typing import Dict
from typing import List
from typing import Set

from models.file_ops_models import FileOperationTarget
from resources.helpers import get_resource_bygeid
from resources.helpers import get_resource_type


@unique
class ResourceType(str, Enum):
    FOLDER = 'Folder'
    FILE = 'File'
    TRASH_FILE = 'TrashFile'
    CONTAINER = 'Container'


class Node(dict):
    """Store information about one node."""

    @property
    def geid(self) -> str:
        return self['global_entity_id']

    @property
    def name(self) -> str:
        return self['name']


class NodeList(list):
    """Store list of Nodes."""

    def __init__(self, nodes: List[Dict[str, Any]]) -> None:
        super().__init__([Node(node) for node in nodes])

    @property
    def geids(self) -> Set[str]:
        return {node.geid for node in self}

    @property
    def names(self) -> List[str]:
        return [node.name for node in self]

    def _get_by_resource_type(self, resource_type: ResourceType) -> List[Node]:
        return [source for source in self if source['resource_type'] == resource_type]

    def filter_folders(self) -> List[Node]:
        """Return sources with folder resource type."""
        return self._get_by_resource_type(ResourceType.FOLDER)

    def filter_files(self) -> List[Node]:
        """Return sources with file resource type."""
        return self._get_by_resource_type(ResourceType.FILE)


class BaseDispatcher:
    """Base class for all dispatcher implementations."""

    async def is_valid_folder_node(self, geid: str) -> bool:
        node = await get_resource_bygeid(geid)

        if node:
            resource_type = get_resource_type(node['labels'])
            if resource_type in [ResourceType.FOLDER, ResourceType.CONTAINER]:
                return True

        return False

    async def validate_targets(self, targets: List[FileOperationTarget]) -> NodeList:
        fetched = []

        for target in targets:
            source = await get_resource_bygeid(target.geid)
            if not source:
                raise ValueError(f'Not found resource: {target.geid}')
            if source['archived'] is True:
                raise ValueError(f'Archived files should not perform further file actions: {target.geid}')
            resource_type = get_resource_type(source['labels'])
            if resource_type not in [ResourceType.FILE, ResourceType.FOLDER]:
                raise ValueError(f'Invalid target type (only support File or Folder): {source}')
            fetched.append(source)

        return NodeList(fetched)

    def execute(self, *args, **kwds):
        raise NotImplementedError
