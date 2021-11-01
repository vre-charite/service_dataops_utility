import time

import requests
from fastapi import APIRouter
from fastapi_utils.cbv import cbv

from config import ConfigClass
from models.base_models import APIResponse, EAPIResponseCode
from models.tags_models import TagsAPIPOST, SysTagsAPIPOST
from resources.error_handler import catch_internal
from resources.utils import validate_taglist
from services.service_logger.logger_factory_service import SrvLoggerFactory
from resources.helpers import get_resource_bygeid
router = APIRouter()

_logger = SrvLoggerFactory('api_tags').get_logger()
OPERATION_TERMINATED = "terminated"
OPERATION_SUCCESS = "success"
LIMIT_REACHED = "limit_reached"


# tags api
    # update new tags list for current entity
    # add new tags list to old tags list for nested folders/files if inherit is true
# system tags api
    # add new tags to current entity and also nested if inherit is true
@cbv(router)
class TagsAPIV2:
    def __init__(self):
        self._logger = SrvLoggerFactory('api_tags').get_logger()

    @router.post('/{geid}/tags', summary="API to add / remove tags for an entity file/folder")
    @catch_internal("api_tags")
    async def post(self, geid: str, entity: str, data: TagsAPIPOST):
        _res = APIResponse()
        data_tags = data.tags
        inherit = data.inherit
        final_res = []
        if not geid or not isinstance(data_tags, list) or not isinstance(geid, str):
            self._logger.error("Tags and geid are required")
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
            self._logger.info("Fetch tags and entity_id from neo4j")

            response = requests.post(ConfigClass.NEO4J_SERVICE + f'nodes/{entity}/query',
                                     json={"global_entity_id": geid})
            if len(response.json()) == 0:
                self._logger.info(f"{entity} does not exist")
                _res.code = EAPIResponseCode.not_found
                _res.error_msg = f"{entity} does not exist"
                return _res.json_response()
            final_update_list = []
            response = response.json()
            entity_update = {
                "global_entity_id": geid,
                "tags": data_tags
            }
            final_update_list.append(entity_update)

            # entity is folder and inherit is true, add new tags list to old tags of child nodes under "tags"
            if inherit and entity == "Folder":
                res = update_tags_nested_entity(tag_type="tags", geid=geid, tags=data_tags)
                final_update_list += res

            #  call neo4j api bulk update
        except Exception as error:
            self._logger.error(f"Error while including tags : {error}")
            _res.code = EAPIResponseCode.internal_error
            _res.error_msg = f"Error while including tags : {error}"
            return _res.json_response(), _res.code


def update_tags_nested_entity(geid, tags, tag_type):
    response = requests.get(ConfigClass.NEO4J_SERVICE + f"relations/connected/{geid}?direction=output")
    api_res = []
    if not len(response.json()["result"]) == 0:
        data = response.json()["result"]
        for child in data:
            child_geid = child["global_entity_id"]
            child_tags = child.get(tag_type, [])
            entity_type = get_resource_type(child["labels"])
            display_path = child["full_path"] if entity_type == "File" else child[
                "folder_relative_path"]
            _logger.info(f"Adding new list of tags to given entity {child_geid}")
            updated_list = tags + child_tags
            updated_tags = list(dict.fromkeys(updated_list))
            if len(updated_tags) > 10:
                current_entity_res = {
                    "name": child["name"],
                    "geid": child["global_entity_id"],
                    "display_path": display_path,
                    tag_type: child_tags,
                    "operation_status": OPERATION_TERMINATED,
                    "error_type": LIMIT_REACHED
                }
            res = {
                "id": child["id"],
                "label": entity_type,
                "properties": {
                    tag_type: updated_list
                }
            }
            api_res.extend(res)
            if entity_type == "File":
                update_elastic_search_entity(geid=child["global_entity_id"], taglist=updated_list, tag_type=tag_type)
    return api_res


def update_tags(entity_geid, tags_list, tag_type):
    final_res = []
    entity_details = get_resource_bygeid(entity_geid)
    if not entity_details:
        raise Exception("Not found resource: " + entity_geid)
    entity_type = get_resource_type(entity_details["labels"])
    entity_id = entity_details["id"]
    try:
        entity_tags = entity_details.get(tag_type, [])
    except KeyError as error:
        entity_tags = []
        _logger.error("No tags for the entity")
    entity_geid = entity_details["global_entity_id"]
    display_path = entity_details["full_path"] if entity_type == "File" else entity_details["folder_relative_path"]
    updated_tags = list(dict.fromkeys(tags_list))
    if len(updated_tags) > 10:
        current_entity_res = {
            "name": entity_details["name"],
            "geid": entity_details["global_entity_id"],
            "display_path": display_path,
            tag_type: entity_tags,
            "operation_status": OPERATION_TERMINATED,
            "error_type": LIMIT_REACHED
        }
        final_res.append(current_entity_res)
    else :
        _logger.info(f"Updating tag list for entity {entity_geid}")
        tags_list = [tag for tag in entity_tags if tag not in tags]

    # else:
    #     _logger.info(f"Updating tag list for entity {entity_geid}")
    #     # tags_list = [tag for tag in entity_tags if tag not in tags]
    #     neo4j_res = http_neo4j_update_tags(entity_type, entity_id=entity_id, tags_list=updated_tags, tag_type=tag_type)
    #     current_entity_res = {
    #         "name": entity_details["name"],
    #         "geid": entity_details["global_entity_id"],
    #         "display_path": display_path,
    #         tag_type: neo4j_res[0][tag_type],
    #         "operation_status": OPERATION_SUCCESS,
    #         "error_type": None
    #     }
    #     if entity_type == "File":
    #         update_elastic_search_entity(geid=entity_details["global_entity_id"], taglist=updated_tags, tag_type=tag_type)
    #     final_res.append(current_entity_res)
    return final_res


def get_resource_type(labels: list):
    """
    Get resource type by neo4j labels
    """
    resources = ['File', 'Folder']
    for label in labels:
        if label in resources:
            return label
    return None


def update_elastic_search_entity(geid, taglist, tag_type):
    _res = APIResponse()
    es_payload = {
        "global_entity_id": geid,
        "updated_fields": {
            tag_type: taglist,
            "time_lastmodified": time.time()
        }
    }
    es_res = requests.put(ConfigClass.PROVENANCE_SERVICE + 'entity/file', json=es_payload)
    if es_res.status_code != 200:
        _logger.error(f"Error while attaching tags to file in es update:{es_res.json()}")
        _res.set_code = EAPIResponseCode.internal_error
        _res.set_error_msg = f"Elastic Search Error: {es_res.json()}"
        return _res.json_response(), _res.code
    _logger.info('Successfully attach tags to file: {}'.format((es_res.json())))
