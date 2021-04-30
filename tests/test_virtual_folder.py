import unittest
from tests.logger import Logger
from tests.prepare_test import SetUpTest

class TestFileMetaCheck(unittest.TestCase):
    log = Logger(name='test_meta_api.log')
    test = SetUpTest(log)
    project_code = "unittest_dataops_ut_vfolders"
    container_id = ''
    headers = {}
    virtual_folder_ids = []
    virtual_folder_geids = []

    @classmethod
    def setUpClass(cls):
        cls.log = cls.test.log
        cls.app = cls.test.app
        cls.headers["Authorization"] = cls.test.auth_member()
        cls.user = cls.test.get_user()
        try:
            cls.container = cls.test.create_project(cls.project_code)
            cls.container_id = cls.container["id"]
            cls.test.add_user_to_project(cls.user["id"], cls.container_id, "admin")
        except Exception as e:
            cls.log.error(f"Failed set up test due to error: {e}")
            raise unittest.SkipTest(f"Failed setup test {e}")

    @classmethod
    def tearDownClass(cls):
        cls.log.info("\n")
        cls.log.info("START TEAR DOWN PROCESS")
        cls.test.delete_node("Dataset", cls.container_id)
        for id in cls.virtual_folder_ids:
            cls.test.delete_node("VirtualFolder", id)

    def test_01_create_vfolder(self):
        payload = {
            "name": "unit_test_vfolder",
            "container_id": self.container_id,
        }
        response = self.app.post("/v1/vfolders/", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200) 
        result = response.json()["result"]
        self.assertEqual(result["container_id"], self.container_id) 
        self.assertEqual(result["name"], "unit_test_vfolder") 
        self.assertTrue("global_entity_id" in result) 
        self.virtual_folder_geids.append(result["global_entity_id"])
        self.virtual_folder_ids.append(result["id"])

    def test_02_get_vfolders(self):
        params = {
            "container_id": self.container_id,
            "order_by": "name",
        }
        response = self.app.get("/v1/vfolders/", params=params, headers=self.headers)
        self.assertEqual(response.status_code, 200) 
        result = response.json()["result"]
        self.assertEqual(result[0]["properties"]["container_id"], self.container_id) 
        self.assertEqual(result[0]["properties"]["name"], "unit_test_vfolder") 

    def test_03_post_vfolders_permissions(self):
        self.test.remove_user_from_project(self.user["id"], self.container_id)
        payload = {
            "name": "unit_test_vfolder",
            "container_id": self.container_id,
        }
        response = self.app.post("/v1/vfolders/", json=payload, headers=self.headers)
        self.test.add_user_to_project(self.user["id"], self.container_id, "contributor")
        self.assertEqual(response.status_code, 403) 
        self.assertEqual(response.json()["error_msg"], "User doesn't belong to project") 


    def test_04_post_vfolders_duplicate(self):
        payload = {
            "name": "unit_test_vfolder_dup",
            "container_id": self.container_id,
        }
        response = self.app.post("/v1/vfolders/", json=payload, headers=self.headers)
        result = response.json()["result"]
        self.virtual_folder_geids.append(result["global_entity_id"])
        self.virtual_folder_ids.append(result["id"])

        response = self.app.post("/v1/vfolders/", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 409) 
        self.assertEqual(response.json()["error_msg"], "Found duplicate folder") 

    def test_05_create_vfolder_admin(self):
        payload = {
            "name": "unit_test_vfolder3",
            "container_id": self.container_id,
        }
        headers = {}
        headers["Authorization"] = self.test.auth()
        response = self.app.post("/v1/vfolders/", json=payload, headers=headers)
        self.assertEqual(response.status_code, 200) 
        result = response.json()["result"]
        self.assertEqual(result["container_id"], self.container_id) 
        self.assertEqual(result["name"], "unit_test_vfolder3") 
        self.assertTrue("global_entity_id" in result) 
        self.virtual_folder_geids.append(result["global_entity_id"])
        self.virtual_folder_ids.append(result["id"])

    def test_06_bulk_update(self):
        payload = {
            "vfolders": [
                 {
                    "name": "unit_test_vfolder2",
                    "geid": self.virtual_folder_geids[0],
                },
            ],
        }
        response = self.app.put("/v1/vfolders/", json=payload, headers=self.headers)
        results = response.json()["result"]
        self.assertEqual(response.status_code, 200) 
        self.assertEqual(results[0]["global_entity_id"], self.virtual_folder_geids[0]) 

    def test_07_bulk_update_permissions(self):
        payload = {
            "vfolders": [
                 {
                    "name": "unit_test_vfolder2",
                    "geid": self.virtual_folder_geids[0],
                },
            ],
        }
        headers = {}
        headers["Authorization"] = self.test.auth()
        response = self.app.put("/v1/vfolders/", json=payload, headers=headers)
        results = response.json()["result"]
        self.assertEqual(response.status_code, 403) 
        self.assertEqual(response.json()["error_msg"], "Permission Denied") 

    def test_08_bulk_update_missing_attr(self):
        payload = {
            "vfolders": [
                 {
                    "name": "unit_test_vfolder2",
                    #"geid": self.virtual_folder_geids[0],
                },
            ],
        }
        headers = {}
        headers["Authorization"] = self.test.auth()
        response = self.app.put("/v1/vfolders/", json=payload, headers=headers)
        results = response.json()["result"]
        self.assertEqual(response.status_code, 400) 
        self.assertEqual(response.json()["error_msg"], "Missing required attribute geid") 

    def test_09_bulk_update_admin(self):
        payload = {
            "vfolders": [
                 {
                    "name": "unit_test_vfolder4",
                    "geid": self.virtual_folder_geids[2],
                },
            ],
        }
        headers = {}
        headers["Authorization"] = self.test.auth()
        response = self.app.put("/v1/vfolders/", json=payload, headers=headers)
        results = response.json()["result"]
        self.assertEqual(response.status_code, 200) 
        self.assertEqual(results[0]["global_entity_id"], self.virtual_folder_geids[2]) 
