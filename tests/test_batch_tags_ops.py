import shutil
import unittest
from unittest import result
from tests.logger import Logger
from tests.prepare_test import SetUpTest
import os
from config import ConfigClass


default_project_code = "dataops_utility_system_tag"
default_folder_name = "test_tag_folder"

def setUpModule():
    _log = Logger(name='test_api_sys_tags.log')
    _test = SetUpTest(_log)
    project_details = _test.get_project_details(default_project_code)
    if len(project_details) > 0:
        project_id = _test.get_project_details(default_project_code)[0].get('id')
        _log.info(f'Existing project_id: {project_id}')
        _test.delete_node("Container", project_id)
    folder_details = _test.get_folder_details('dataops_utility_system_tag_folder')
    if len(folder_details) > 0:
        folder_id = folder_details[0]['id']
        if folder_id:
            _test.delete_folder_node(folder_id)
@unittest.skip('need update')
class TestAPISYSTags(unittest.TestCase):
    container = None
    folder = None
    log = Logger(name='test_api_sys_tags.log')
    test = SetUpTest(log)
    project_code = "dataops_utility_system_tag"
    container_id = ''
    folder_id = ''

    @classmethod
    def setUpClass(cls):
        cls.log = cls.test.log
        cls.app = cls.test.app

        try:
            # cls.container = cls.test.get_project_details(cls.project_code)
            cls.container = cls.test.create_project(cls.project_code, name="DataopsUTUnitTestTags")
            cls.container_geid = cls.container["global_entity_id"]
            cls.container_id = cls.container["id"]
            cls.folder = cls.test.create_folder(cls.project_code)
            cls.folder_name = cls.folder.get("result")["name"]
            cls.folder_id = cls.folder.get("result")['id']
            print(cls.folder.get("result")["global_entity_id"])
            if cls.folder is not None:
                cls.folder_geid = cls.folder.get("result")["global_entity_id"]
        except Exception as e:
            cls.log.error(f"Failed set up test due to error: {e}")
            raise Exception(f"Failed setup test {e}")

    @classmethod
    def tearDownClass(cls):
        cls.log.info("\n")
        cls.log.info("START TEAR DOWN PROCESS")
        cls.test.delete_node("Container", cls.container_id)
        cls.test.delete_folder_node(cls.folder_id)

    def test_01_attach_tags_folder(self):
        self.log.info("Attach tags to given folder")
        # folder_geid = "bc40d711-5b4f-499a-baf2-2d5d61f43ef8-1621605201"
        payload = {
                "entity": [
                    self.folder_geid
                ],
                "tags": ["a","l","f"],
                "inherit": "False",
                "operation": "add"
        }
        try:
            response = self.app.post(f"/v2/entity/tags", json=payload)
            self.log.info(f"POST RESPONSE: {response}")
            self.log.info(f"COMPARING: {response.status_code} VS {200}")
            self.assertEqual(response.status_code, 200)
        except Exception as e:
            self.log.error(e)
            raise e

    def test_02_remove_tags_folder(self):
        self.log.info("Attach tags to given folder")
        # folder_geid = "bc40d711-5b4f-499a-baf2-2d5d61f43ef8-1621605201"
        payload = {
                "entity": [
                    self.folder_geid
                ],
                "tags": ["a","f"],
                "inherit": "False",
                "operation": "remove"
        }
        try:
            response = self.app.post(f"/v2/entity/tags", json=payload)
            self.log.info(f"POST RESPONSE: {response}")
            self.log.info(f"COMPARING: {response.status_code} VS {200}")
            self.assertEqual(response.status_code, 200)
        except Exception as e:
            self.log.error(e)
            raise e

    def test_03_tag_validation(self):
        self.log.info("Attach tags to given folder")
        # folder_geid = "bc40d711-5b4f-499a-baf2-2d5d61f43ef8-1621605201"
        payload = {
            "entity": [
                self.folder_geid
            ],
            "tags": ["c1___"],
            "inherit": "False",
            "operation": "remove"
        }
        try:
            response = self.app.post(f"/v2/entity/tags", json=payload)
            self.log.info(f"POST RESPONSE: {response}")
            self.log.info(f"COMPARING: {response.status_code} VS {200}")
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()["error_msg"], "Invalid tags : invalid tag, must be 1-32 characters "
                                                           "lower case, number or hyphen")
        except Exception as e:
            self.log.error(e)
            raise e