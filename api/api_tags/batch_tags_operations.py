""" Batch tag operation API"""
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
        """ API to perform batch operation for tags"""
        _res = APIResponse()
        entity_geid_list = data.entity
        data_tags = data.tags
        operation = data.operation
        inherit = data.inherit
        only_files = data.only_files
        final_response = []

        valid, validate_data = validate_taglist(data_tags, inherit)
        if not valid:
            self._logger.error(f"Invalid tags : {validate_data['error']}")
            _res.error_msg = f"Invalid tags : {validate_data['error']}"
            _res.code = EAPIResponseCode.bad_request
            return _res.json_response()

        try:
            for entity_geid in entity_geid_list:
                _logger.info(f"Fetch details of given entity : {entity_geid}")
                entity_details = get_resource_bygeid(entity_geid)
                entity_type = get_resource_type(entity_details["labels"])

                # can be File also
                if only_files and entity_type == "Folder":
                    only_files_res = update_only_files(
                        entity_geid, data_tags, operation)
                    final_response.extend(only_files_res)
                else:
                    _logger.info(f"updating current entity :{entity_geid}")
                    current_entity_res = update_tag_list_based_on_operation(entity_geid=entity_geid, tags=data_tags,
                                                                            operation=operation)
                    final_response.append(current_entity_res)

                    if current_entity_res["operation_status"] == 'success':
                        _logger.info("Updating elastic search entity with tag list")
                        update_elastic_search_entity(geid=entity_details["global_entity_id"],
                                                     taglist=current_entity_res["tags"])

                    if entity_type == "Folder" and inherit is True and not only_files:
                        _logger.info(
                            f"Updating nested entity for entity : {entity_geid}")
                        child_tags = update_tags_nested_entity(
                            geid=entity_geid, tags=data_tags, operation=operation)
                        if len(child_tags) != 0:
                            final_response.extend(child_tags)

            final_response.append({"total": len(final_response)})
            _res.code = EAPIResponseCode.success

            _res.result = final_response

            _logger.info(
                f"Batch tags operation successful for  given entities : {final_response}")
            return _res.json_response()
        except Exception as error:
            _logger.error(
                f"Error while performing batch tag operation : {error}")
            _res.code = EAPIResponseCode.internal_error
            _res.result = "Error while performing batch tag operation"
            return _res.json_response()


def http_neo4j_update_tags(entity, entity_id, tags_list):
    """ Update tags list in neo4j"""
    _res = APIResponse()
    _logger.info("Update tags for the given entity")
    payload = {
        "tags": tags_list
    }
    res = requests.put(ConfigClass.NEO4J_SERVICE +
                       f"nodes/{entity}/node/{entity_id}", json=payload)
    if res.status_code != 200:
        _logger.error("Error while updating tags in neo4j")
        _res.set_code = EAPIResponseCode.internal_error
        _res.set_error_msg = f"Error while updating tags in neo4j: {res.json()}"
        return _res.json_response()
    return res.json()


def update_tags_nested_entity(geid, tags, operation):
    """ Update tags for nested entity"""
    _res = APIResponse()
    try:
        response = requests.get(
            ConfigClass.NEO4J_SERVICE + f"relations/connected/{geid}?direction=output")
        api_res = []
        if not len(response.json()["result"]) == 0:
            data = response.json()["result"]
            for child in data:
                api_res_entity = update_tag_list_based_on_operation(operation=operation,
                                                                    entity_geid=child["global_entity_id"], tags=tags)
                api_res.append(api_res_entity)
                # get proper file/folder form labels list
                # if api_res[0]["operation_status"] == "success":
                _logger.info(f"Updating elastic search entity with tag list for : {child['global_entity_id']}")
                child_geid = child["global_entity_id"]
                update_elastic_search_entity(
                    geid=child_geid, taglist=api_res[0]["tags"])
        return api_res
    except Exception as error:
        _logger.error(
            f"Error while updating tags for child entities : {error}")
        _res.set_code = EAPIResponseCode.internal_error
        _res.set_error_msg = f"Error while updating tags for child entities : {error}"
        return _res.json_response(), _res.code


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
    es_res = requests.put(ConfigClass.PROVENANCE_SERVICE +
                          'entity/file', json=es_payload)
    if es_res.status_code != 200:
        _logger.error(
            f"Error while attaching tags to file in es update:{es_res.json()}")
        _res.set_code = EAPIResponseCode.internal_error
        _res.set_error_msg = f"Elastic Search Error: {es_res.json()}"
        return _res.json_response(), _res.code
    _logger.info(
        'Successfully attach tags to file: {}'.format((es_res.json())))


def get_resource_type(labels: list):
    """
    Get resource type by neo4j labels
    """
    resources = ['File', 'Folder']
    for label in labels:
        if label in resources:
            return label
    return None


def update_tag_list_based_on_operation(operation, entity_geid, tags):
    current_entity_res = {}
    entity_details = get_resource_bygeid(entity_geid)
    entity_type = get_resource_type(entity_details["labels"])
    entity_id = entity_details["id"]
    entity_tags = entity_details["tags"]
    entity_geid = entity_details["global_entity_id"]
    display_path = entity_details["full_path"] if entity_type == "File" else entity_details["folder_relative_path"]
    if operation == "add":
        _logger.info(f"Adding new list of tags to given entity {entity_geid}")
        updated_list = tags + entity_tags
        tags_list = list(dict.fromkeys(updated_list))

        if len(tags_list) > 10:
            _logger.info(
                f"List of tags exceed limit 10 for {entity_geid} : {tags_list}")
            current_entity_res = {
                "name": entity_details["name"],
                "geid": entity_details["global_entity_id"],
                "display_path": display_path,
                "tags": entity_tags,
                "operation_status": OPERATION_TERMINATED,
                "error_type": LIMIT_REACHED
            }
            return current_entity_res
            # final_res.append(current_entity_res)
        else:
            _logger.info(
                f"List of tags being added to entity {entity_geid} : {tags_list}")
            neo4j_res = http_neo4j_update_tags(
                entity_type, entity_id=entity_id, tags_list=tags_list)
            current_entity_res = {
                "name": entity_details["name"],
                "geid": entity_details["global_entity_id"],
                "display_path": display_path,
                "tags": neo4j_res[0]["tags"],
                "operation_status": OPERATION_SUCCESS,
                "error_type": None
            }
            # final_res.append(current_entity_res)
    if operation == "remove":
        _logger.info(f"Removing list of tags from given entity {entity_geid}")
        tags_list = [tag for tag in entity_tags if tag not in tags]
        neo4j_res = http_neo4j_update_tags(
            entity_type, entity_id=entity_id, tags_list=tags_list)
        current_entity_res = {
            "name": entity_details["name"],
            "geid": entity_details["global_entity_id"],
            "display_path": display_path,
            "tags": neo4j_res[0]["tags"],
            "operation_status": OPERATION_SUCCESS,
            "error_type": None
        }
        # final_res.append(current_entity_res)
    return current_entity_res


def update_only_files(entity_geid, data_tags, operation):
    _logger.info(f"Updating only files under given entity : {entity_geid}")
    response = requests.get(ConfigClass.NEO4J_SERVICE +
                            f"relations/connected/{entity_geid}?direction=output")
    api_res = []
    if not len(response.json()["result"]) == 0:
        data = response.json()["result"]
        for child in data:
            child_geid = child["global_entity_id"]
            entity_details = get_resource_bygeid(child_geid)
            entity_type = get_resource_type(entity_details["labels"])
            if entity_type == "File":
                api_res_entity = update_tag_list_based_on_operation(entity_geid=child_geid, tags=data_tags,
                                                                    operation=operation)
                api_res.append(api_res_entity)
                if api_res[0]["operation_status"] == "success":
                    _logger.info("Updating elastic search entity with tag list")
                    update_elastic_search_entity(
                        geid=child_geid, taglist=api_res[0]["tags"])
    return api_res
