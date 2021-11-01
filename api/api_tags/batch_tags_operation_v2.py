""" Batch tag operation API refactored to update tags using batch update in neo4j"""
import time

import requests
from fastapi import APIRouter
from fastapi_utils.cbv import cbv

from config import ConfigClass
from models.base_models import APIResponse, EAPIResponseCode
from models.tags_models import BatchOpsTagsPOST
from resources.helpers import get_resource_bygeid
from resources.utils import validate_taglist
from services.service_logger.logger_factory_service import SrvLoggerFactory

router = APIRouter()

_logger = SrvLoggerFactory('batch_tags_ops').get_logger()
OPERATION_TERMINATED = "terminated"
OPERATION_SUCCESS = "success"
LIMIT_REACHED = "limit_reached"


@cbv(router)
class BatchOpsTagsAPI:
    def __init__(self):
        self._logger = SrvLoggerFactory('batch_ops').get_logger()

    @router.post("/tags")
    # @catch_internal("batch_tags_operation")
    def batch_tags_ops(self, data: BatchOpsTagsPOST):
        """ Batch tag operation API refactored to update tags using batch update in neo4j"""

        _res = APIResponse()
        entity_geid_list = data.entity
        data_tags = data.tags
        operation = data.operation
        inherit = data.inherit
        only_files = data.only_files
        final_response = []
        batch_update_neo4j_list = []
        valid, validate_data = validate_taglist(data_tags, inherit)
        if not valid:
            self._logger.error(f"Invalid tags : {validate_data['error']}")
            _res.error_msg = f"Invalid tags : {validate_data['error']}"
            _res.code = EAPIResponseCode.bad_request
            return _res.json_response()
        try:
            for entity_geid in entity_geid_list:
                entity_details = get_resource_bygeid(entity_geid, exclude_archived=True)
                entity_type = get_resource_type(entity_details["labels"])
                if only_files and entity_type == "Folder":
                    only_files_res, batch_update_list  = update_only_files(entity_geid, data_tags, operation)
                    final_response.extend(only_files_res)
                    if batch_update_list:
                        batch_update_neo4j_list += batch_update_list
                else:
                    _logger.info(f"updating current entity :{entity_geid}")
                    current_entity_res, batch_update = update_tag_list_based_on_operation(entity_geid=entity_geid, tags=data_tags,
                                                                            operation=operation)
                    if current_entity_res:
                        final_response.append(current_entity_res)
                    if batch_update:
                        batch_update_neo4j_list += batch_update
                    if entity_type == "Folder" and inherit is True and not only_files:
                        _logger.info(f"Updating nested entity for entity : {entity_geid}")
                        child_tags, batch_update_child = update_tags_nested_entity(geid=entity_geid, tags=data_tags, operation=operation)
                        if len(child_tags) != 0:
                            final_response.extend(child_tags)
                            batch_update_neo4j_list += batch_update_child
                    if current_entity_res["operation_status"] == 'success':
                        _logger.info("Updating root entity. Updating elastic search entity with tag list")
                        update_elastic_search_entity(geid=entity_details["global_entity_id"],
                                taglist=current_entity_res["tags"])
            final_response.append({"total": len(final_response)})

            neo4j_res = http_query_batch_update_neo4j(batch_update_neo4j_list)
            if neo4j_res.status_code != 200:
                _logger.error("Error while updating tags in neo4j")
                _res.code = EAPIResponseCode.internal_error
                _res.error_msg = f"Error while updating tags in neo4j: {neo4j_res.json()}"
                return _res.json_response()
            _res.code = EAPIResponseCode.success

            _res.result = final_response

            _logger.info(f"Batch tags operation successful for  given entities : {final_response}")
            return _res.json_response()
        except Exception as error:
            _logger.error(f"Error while performing batch tag operation : {error}")
            _res.code = EAPIResponseCode.internal_error
            _res.result = "Error while performing batch tag operation"
            return _res.json_response()


def http_query_batch_update_neo4j(batch_update_list):
    """ Update tags for list of geids in neo4j"""
    _res = APIResponse()
    _logger.info("Update tags for the given entity")
    node_property = "tags"
    payload = {
        "data": batch_update_list
    }
    res = requests.put(ConfigClass.NEO4J_SERVICE + f"nodes/{node_property}/batch/update", json=payload)
    return res


def update_tag_list_based_on_operation(operation, entity_geid, tags):
    current_entity_res = {}
    batch_update = []
    entity_details = get_resource_bygeid(entity_geid, exclude_archived=True)
    if not entity_details:
        return None, None
    entity_type = get_resource_type(entity_details["labels"])
    entity_tags = entity_details["tags"]
    display_path = entity_details["display_path"] if entity_type == "File" else entity_details["folder_relative_path"]
    if operation == "add":
        updated_list = tags + entity_tags
        tags_list = list(dict.fromkeys(updated_list))

        if len(tags_list) > 10:
            current_entity_res = {
                "name": entity_details["name"],
                "geid": entity_details["global_entity_id"],
                "display_path": display_path,
                "tags": entity_tags,
                "operation_status": OPERATION_TERMINATED,
                "error_type": LIMIT_REACHED
            }
            return current_entity_res, None
        else:
            batch_update.append({
                "global_entity_id": entity_details["global_entity_id"],
                "tags": tags_list
            })
            current_entity_res = {
                "name": entity_details["name"],
                "geid": entity_details["global_entity_id"],
                "display_path": display_path,
                # "tags": neo4j_res[0]["tags"],
                "tags": tags_list,
                "operation_status": OPERATION_SUCCESS,
                "error_type": None
            }
    if operation == "remove":
        tags_list = [tag for tag in entity_tags if tag not in tags]
        batch_update.append({
            "global_entity_id": entity_details["global_entity_id"],
            "tags": tags_list
        })
        current_entity_res = {
            "name": entity_details["name"],
            "geid": entity_details["global_entity_id"],
            "display_path": display_path,
            "tags": tags_list,
            # "tags": neo4j_res[0]["tags"],
            "operation_status": OPERATION_SUCCESS,
            "error_type": None
        }
    return current_entity_res, batch_update


def get_resource_type(labels: list):
    """
    Get resource type by neo4j labels
    """
    resources = ['File', 'Folder']
    for label in labels:
        if label in resources:
            return label
    return None


def update_tags_nested_entity(geid, tags, operation):
    """ Update tags for nested entity"""
    _res = APIResponse()
    batch_update_tags = []
    try:
        response = requests.get(ConfigClass.NEO4J_SERVICE + f"relations/connected/{geid}?direction=output")
        api_res = []
        if not len(response.json()["result"]) == 0:
            data = response.json()["result"]
            for child in data:
                api_res_entity, batch_update_child = update_tag_list_based_on_operation(operation=operation,
                                                                    entity_geid=child["global_entity_id"], tags=tags)
                if api_res_entity:
                    api_res.append(api_res_entity)
                    if batch_update_child is not None:
                        batch_update_tags += batch_update_child
                    # get proper file/folder form labels list
                    if api_res_entity["operation_status"] == "success":
                        child_geid = child["global_entity_id"]
                        update_elastic_search_entity(geid=child_geid, taglist=api_res_entity["tags"])

        _logger.debug(f"update_tags_nested_entity result: {api_res}")
        return api_res, batch_update_tags
    except Exception as error:
        _logger.error(f"Error while updating tags for child entities : {error}")
        _res.code = EAPIResponseCode.internal_error
        _res.error_msg = f"Error while updating tags for child entities : {error}"
        return _res.json_response(), _res.code


def update_only_files(entity_geid, data_tags, operation):
    _logger.info(f"Updating only files under given entity : {entity_geid}")
    response = requests.get(ConfigClass.NEO4J_SERVICE + f"relations/connected/{entity_geid}?direction=output")
    api_res = []
    batch_update_list = []
    if not len(response.json()["result"]) == 0:
        data = response.json()["result"]
        for child in data:
            child_geid = child["global_entity_id"]
            entity_details = get_resource_bygeid(child_geid, exclude_archived=True )
            if not entity_details:
                continue
            entity_type = get_resource_type(entity_details["labels"])
            if entity_type == "File":
                api_res_entity, batch_update = update_tag_list_based_on_operation(entity_geid=child_geid, tags=data_tags,
                                                                    operation=operation)
                if batch_update is not None:
                    batch_update_list += batch_update
                if api_res_entity:
                    api_res.append(api_res_entity)
                if api_res_entity["operation_status"] == "success":
                    _logger.info("Entity is File. Updating elastic search entity with tag list")
                    update_elastic_search_entity(geid=child_geid, taglist=api_res_entity["tags"])
    return api_res, batch_update_list


def update_elastic_search_entity(geid, taglist):
    """ update es entity with new tag list"""
    _res = APIResponse()
    es_payload = {
        "global_entity_id": geid,
        "updated_fields": {
            "tags": taglist,
            "time_lastmodified": time.time()
        }
    }
    es_res = requests.put(ConfigClass.PROVENANCE_SERVICE + 'entity/file', json=es_payload)
    if es_res.status_code != 200:
        _logger.error(f"Error while attaching tags to file in es update:{es_res.json()}")
        _res.code = EAPIResponseCode.internal_error
        _res.error_msg = f"Elastic Search Error: {es_res.json()}"
        return _res.json_response(), _res.code
    _logger.info('Successfully attach tags to file: {}'.format((es_res.json())))
