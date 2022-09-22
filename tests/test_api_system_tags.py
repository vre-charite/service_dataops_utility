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

import unittest

from logger import LoggerFactory

from tests.prepare_test import SetUpTest

default_project_code = "dataops_utility_system_tag"
default_folder_name = "test_tag_folder"


def setUpModule():
    _log = LoggerFactory(name='test_api_sys_tags.log').get_logger()
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
    log = LoggerFactory(name='test_api_sys_tags.log').get_logger()
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
            #cls.folder = cls.test.create_folder(cls.project_code)
            cls.folder_name = cls.folder.get("result")["name"]
            cls.folder_id = cls.folder.get("result")['id']
            print(cls.folder.get("result")["global_entity_id"])
            #if cls.folder is not None:
                #cls.folder_geid = cls.folder.get("result")["global_entity_id"]
        except Exception as e:
            cls.log.error(f"Failed set up test due to error: {e}")
            raise Exception(f"Failed setup test {e}")

    @classmethod
    def tearDownClass(cls):
        cls.log.info("\n")
        cls.log.info("START TEAR DOWN PROCESS")
        cls.test.delete_node("Container", cls.container_id)
        cls.test.delete_folder_node(cls.folder_id)

    @unittest.skip("need update")
    def test_01_attach_sys_tags_folder(self):
        self.log.info("Attach system tags to given folder")
        # folder_geid = "bc40d711-5b4f-499a-baf2-2d5d61f43ef8-1621605201"
        payload = {
            "systags": ["copied-to-core"],
            "inherit": "True"
        }
        try:
            response = self.app.post(f"/v2/Folder/{self.folder_geid}/systags", json=payload)
            self.log.info(f"POST RESPONSE: {response}")
            self.log.info(f"COMPARING: {response.status_code} VS {200}")
            self.assertEqual(response.status_code, 200)
        except Exception as e:
            self.log.error(e)
            raise e

    def test_02_attach_systags_file(self):
        self.log.info("Attach systags to given folder")
        file_geid = "3d44e415-5408-4e19-be0f-8f9d34e3dfb8-1621605093"
        payload = {
            "systags": ["c"],
            "inherit": "True"
        }
        try:
            response = self.app.post(f"/v2/File/{file_geid}/systags", json=payload)
            self.log.info(f"POST RESPONSE: {response}")
            self.log.info(f"COMPARING: {response.status_code} VS {200}")
            self.assertEqual(response.status_code, 200)
        except Exception as e:
            self.log.error(e)
            raise e

    def test_03_attach_systags_folder_inherit_false(self):
        self.log.info("Attach systags to given folder")
        folder_geid = "bc40d711-5b4f-499a-baf2-2d5d61f43ef8-1621605201"
        payload = {
            "systags": ["c"],
            "inherit": "False"
        }
        try:
            response = self.app.post(f"/v2/Folder/{folder_geid}/systags", json=payload)
            self.log.info(f"POST RESPONSE: {response}")
            self.log.info(f"COMPARING: {response.status_code} VS {200}")
            self.assertEqual(response.status_code, 200)
        except Exception as e:
            self.log.error(e)
            raise e

    def test_04_tag_validation(self):
        self.log.info("Attach systags to given folder")
        folder_geid = "bc40d711-5b4f-499a-baf2-2d5d61f43ef8-1621605201"
        payload = {
            "systags": ["c1___"],
            "inherit": "False"
        }
        try:
            response = self.app.post(f"/v2/Folder/{folder_geid}/systags", json=payload)
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
        self.log.info("Attach systags to given folder")
        folder_geid = "bc40d71-499a-baf2-2d5d61f43ef8-1621605201"
        payload = {
            "systags": ["c"],
            "inherit": "False"
        }
        try:
            response = self.app.post(f"/v2/Folder/{folder_geid}/systags", json=payload)
            self.log.info(f"POST RESPONSE: {response}")
            self.log.info(f"COMPARING: {response.status_code} VS {200}")
            self.assertEqual(response.status_code, 404)
        except Exception as e:
            self.log.error(e)
            raise e
