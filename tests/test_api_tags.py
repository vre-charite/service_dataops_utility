import shutil
import unittest
from unittest import result
from tests.logger import Logger
from tests.prepare_test import SetUpTest
import os
from config import ConfigClass


class TestAPITags(unittest.TestCase):
    log = Logger(name='test_api_tags.log')
    test = SetUpTest(log)
    project_code = "jiang0526"
    container_id = ''
    folder_name = ''

    @classmethod
    def setUpClass(cls):
        cls.log = cls.test.log
        cls.app = cls.test.app

        try:
            cls.container = cls.test.get_project_details(cls.project_code)
            cls.container_geid = cls.container[0]["global_entity_id"]
            cls.container_id = cls.container[0]["id"]
            cls.folder = cls.test.create_folder(cls.project_code)
            cls.folder_name = cls.folder.get("result")["name"]
            print(cls.folder)
            print(cls.folder.get("result")["global_entity_id"])
            if cls.folder is not None:
                cls.folder_geid = cls.folder.get("result")["global_entity_id"]
        except Exception as e:
            cls.log.error(f"Failed set up test due to error: {e}")
            raise unittest.SkipTest(f"Failed setup test {e}")

    @classmethod
    def tearDownClass(cls):
        cls.log.info("\n")
        cls.log.info("START TEAR DOWN PROCESS")
        raw_folder_path = os.path.join(
            ConfigClass.ROOT_PATH, cls.project_code, "raw")
        path = os.path.join(raw_folder_path, cls.folder_name)
        # shutil.rmtree(path)
        # os.remove(cls.folder_path)

    def test_01_attach_tags_folder(self):
        self.log.info("Attach tags to given folder")
        # folder_geid = "bc40d711-5b4f-499a-baf2-2d5d61f43ef8-1621605201"
        payload = {
            "tags": ["c"],
            "inherit": "True"
        }
        try:
            response = self.app.post(f"/v2/Folder/{self.folder_geid}/tags", json=payload)
            self.log.info(f"POST RESPONSE: {response}")
            self.log.info(f"COMPARING: {response.status_code} VS {200}")
            self.assertEqual(response.status_code, 200)
        except Exception as e:
            self.log.error(e)
            raise e

    # def test_02_attach_tags_file(self):
    #     self.log.info("Attach tags to given folder")
    #     # file_geid = "3d44e415-5408-4e19-be0f-8f9d34e3dfb8-1621605093"
    #     payload = {
    #         "tags": ["c"],
    #         "inherit": "True"
    #     }
    #     try:
    #         response = self.app.post(f"/v2/File/{self.file_geid}/tags", json=payload)
    #         self.log.info(f"POST RESPONSE: {response}")
    #         self.log.info(f"COMPARING: {response.status_code} VS {200}")
    #         self.assertEqual(response.status_code, 200)
    #     except Exception as e:
    #         self.log.error(e)
    #         raise e

    def test_03_attach_tags_folder_inherit_false(self):
        self.log.info("Attach tags to given folder")
        # folder_geid = "bc40d711-5b4f-499a-baf2-2d5d61f43ef8-1621605201"
        payload = {
            "tags": ["c"],
            "inherit": "False"
        }
        try:
            response = self.app.post(f"/v2/Folder/{self.folder_geid}/tags", json=payload)
            self.log.info(f"POST RESPONSE: {response}")
            self.log.info(f"COMPARING: {response.status_code} VS {200}")
            self.assertEqual(response.status_code, 200)
        except Exception as e:
            self.log.error(e)
            raise e

    def test_04_tag_validation(self):
        self.log.info("Attach tags to given folder")
        # folder_geid = "bc40d711-5b4f-499a-baf2-2d5d61f43ef8-1621605201"
        payload = {
            "tags": ["c1___"],
            "inherit": "False"
        }
        try:
            response = self.app.post(f"/v2/Folder/{self.folder_geid}/tags", json=payload)
            self.log.info(f"POST RESPONSE: {response}")
            self.log.info(f"COMPARING: {response.status_code} VS {200}")
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()["error_msg"], "Invalid tags : invalid tag, must be 1-32 characters lower "
                                                           "case, "
                                                           "number or hyphen")
        except Exception as e:
            self.log.error(e)
            raise e

    def test_05_entity_not_found(self):
        self.log.info("Attach tags to given folder")
        folder_geid = "bc40d711-f-499a-baf2-2d5d61f43ef8-1621605201"
        payload = {
            "tags": ["c"],
            "inherit": "False"
        }
        try:
            response = self.app.post(f"/v2/Folder/{folder_geid}/tags", json=payload)
            self.log.info(f"POST RESPONSE: {response}")
            self.log.info(f"COMPARING: {response.status_code} VS {200}")
            self.assertEqual(response.status_code, 404)
        except Exception as e:
            self.log.error(e)
            raise e
