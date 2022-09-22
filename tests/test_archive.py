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


class TestArchive(unittest.TestCase):
    log = LoggerFactory(name='test_archive_api.log').get_logger()
    test = SetUpTest(log)
    project_code = "unittest_archive_dataops_util"
    container_id = ''
    file_id = []

    @classmethod
    def setUpClass(cls):
        cls.log = cls.test.log
        cls.app = cls.test.app
        file_data = {
            'filename': 'dataops_gr_archive_test_1.zip',
            'namespace': 'greenroom',
            'project_code': cls.project_code,
            'uploader': 'DataopsGRUnittest'
        }
        try:
            cls.container_id = cls.test.create_project(cls.project_code, name="DataopsUTArchiveTest")["id"]
            cls.file_geid = "fakearchiveunittestgeid"
        except Exception as e:
            print(e)
            cls.log.error(f"Failed set up test due to error: {e}")
            raise Exception(f"Failed setup test {e}")

    @classmethod
    def tearDownClass(cls):
        cls.log.info("\n")
        cls.log.info("START TEAR DOWN PROCESS")
        try:
            cls.test.delete_node("Container", cls.container_id)
            payload = {
                "file_geid": cls.file_geid,
            }
            cls.app.delete("/v1/archive", json=payload)
        except Exception as e:
            cls.log.error("Please manual delete node and entity")
            cls.log.error(e)
            raise e

    def test_01_create_preview(self):
        self.log.info("\n")
        self.log.info("01 test create_preview".center(80, '-'))
        payload = {
            "file_geid": self.file_geid,
            "archive_preview": {'QAZ-1234_ABC-1234_Dicomzip_Prüfung_edited153928o': {'ABC-1234_Dicomzip_Prüfung200140o': {'101_DTI': {'is_dir': True}}}}
        }
        result = self.app.post(f"/v1/archive", json=payload)
        print(result)
        print(result.content)
        data = result.json()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(data["result"], "success")

    def test_02_get_preview(self):
        self.log.info("\n")
        self.log.info("02 test get_preview".center(80, '-'))
        payload = {
            "file_geid": self.file_geid,
        }
        result = self.app.get(f"/v1/archive", params=payload)
        data = result.json()
        print(data)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(data["result"], {'QAZ-1234_ABC-1234_Dicomzip_Prüfung_edited153928o': {'ABC-1234_Dicomzip_Prüfung200140o': {'101_DTI': {'is_dir': True}}}})

    def test_03_get_preview_missing_geid(self):
        self.log.info("\n")
        self.log.info("03 test get_preview_missing_geid".center(80, '-'))
        payload = {
        }
        result = self.app.get(f"/v1/archive", params=payload)
        data = result.json()
        self.assertEqual(result.status_code, 422)
        self.assertEqual(data["detail"][0]["msg"], "field required")

    def test_04_get_preview_file_not_found(self):
        self.log.info("\n")
        self.log.info("04 test get_preview_file_not_found".center(80, '-'))
        payload = {
            "file_geid": "notfound",
        }
        result = self.app.get(f"/v1/archive", params=payload)
        data = result.json()
        self.assertEqual(result.status_code, 404)
        self.assertEqual(data["result"], "Archive preview not found")
