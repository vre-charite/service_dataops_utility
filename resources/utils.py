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
import time
from config import ConfigClass
import httpx
from models.base_models import APIResponse
from models.base_models import EAPIResponseCode
from logger import LoggerFactory

_logger = LoggerFactory('tags_ops').get_logger()


def get_resource_type(labels: list):
    """
    Get resource type by neo4j labels
    """
    resources = ['File', 'Folder']
    for label in labels:
        if label in resources:
            return label
    return None


def validate_taglist(taglist, internal=False):
    tag_requirement = re.compile("^[a-z0-9-]{1,32}$")
    for tag in taglist:
        if tag == "copied-to-core" and not internal:
            return False, {
                "error": 'invalid tag, tag is reserved',
                "code": EAPIResponseCode.forbidden
            }
        if not re.search(tag_requirement, tag):
            return False, {
                "error": 'invalid tag, must be 1-32 characters lower case, number or hyphen',
                "code": EAPIResponseCode.forbidden
            }

    # duplicate check
    if len(taglist) != len(set(taglist)):
        return False, {
            "error": 'duplicate tags not allowed',
            "code": EAPIResponseCode.bad_request
        }

    if len(taglist) > 10:
        return False, {
            "error": 'limit of 10 tags',
            "code": EAPIResponseCode.bad_request
        }
    return True, {}


async def http_update_node(primary_label, neo4j_id, update_json):
    # update neo4j node
    update_url = ConfigClass.NEO4J_SERVICE + \
                 "nodes/{}/node/{}".format(primary_label, neo4j_id)
    async with httpx.AsyncClient() as client:
        res = await client.put(url=update_url, json=update_json)
    return res


async def update_elastic_search_entity(geid, taglist, tag_type):
    _res = APIResponse()
    es_payload = {
        "global_entity_id": geid,
        "updated_fields": {
            tag_type: taglist,
            "time_lastmodified": time.time()
        }
    }
    async with httpx.AsyncClient() as client:
        es_res = await client.put(ConfigClass.PROVENANCE_SERVICE +
                            'entity/file', json=es_payload)
    if es_res.status_code != 200:
        _logger.error(
            f"Error while attaching tags to file in es update:{es_res.json()}")
        _res.set_code = EAPIResponseCode.internal_error
        _res.set_error_msg = f"Elastic Search Error: {es_res.json()}"
        return _res.json_response(), _res.code
    _logger.info(
        'Successfully attach tags to file: {}'.format((es_res.json())))
