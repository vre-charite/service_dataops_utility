import random
from typing import Callable

import pytest

from api.api_file_operations.copy_dispatcher import ResourceType
from api.api_file_operations.copy_dispatcher import Source
from api.api_file_operations.copy_dispatcher import SourceList


@pytest.fixture
def generate_source() -> Callable[..., Source]:
    def _generate_source(resource_type=None) -> Source:
        resource_type = resource_type or random.choice(list(ResourceType))

        return Source(
            {
                'resource_type': resource_type,
            }
        )

    return _generate_source


class TestSourceList:
    def test_new_instance_converts_list_values_into_source_instances(self):
        sources = SourceList([{'key': 'value'}])

        assert isinstance(sources[0], Source)

    def test_filter_folders_returns_sources_with_folder_resource_type(self, generate_source):
        expected_source = generate_source(resource_type=ResourceType.FOLDER)

        sources = SourceList([generate_source(resource_type=ResourceType.FILE), expected_source])

        assert sources.filter_folders() == [expected_source]

    def test_filter_files_returns_sources_with_file_resource_type(self, generate_source):
        expected_source = generate_source(resource_type=ResourceType.FILE)

        sources = SourceList([generate_source(resource_type=ResourceType.FOLDER), expected_source])

        assert sources.filter_files() == [expected_source]
