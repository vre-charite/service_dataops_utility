import unittest
from unittest import result
from tests.logger import Logger
from tests.prepare_test import SetUpTest

# @unittest.skip("need update")
class TestVirtualFoldersCheck(unittest.TestCase):
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
            cls.container = cls.test.create_project(cls.project_code, name="DataopsUTUnitTestVfolder")
            cls.container_geid = cls.container["global_entity_id"]
            cls.container_id = cls.container["id"]
            cls.test.add_user_to_project(cls.user["id"], cls.container_id, "admin")
        except Exception as e:
            cls.log.error(f"Failed set up test due to error: {e}")
            raise Exception(f"Setup failed: {e}")

    @classmethod
    def tearDownClass(cls):
        cls.log.info("\n")
        cls.log.info("START TEAR DOWN PROCESS")
        cls.test.delete_node("Container", cls.container_id)
        for id in cls.virtual_folder_geids:
            cls.test.delete_node("VirtualFolder", id)

    def test_01_create_vfolder(self):
        self.log.info("\n")
        self.log.info('01'+'test create collection'.center(80, '-'))
        payload = {
            "name": "unit_test_vfolder",
            "project_geid": self.container_geid,
            "username": self.user["username"]
        }
        try:
            response = self.app.post("/v1/collections/", json=payload, headers=self.headers)
            self.log.info(f"POST RESPONSE: {response}")
            self.log.info(f"COMPARING: {response.status_code} VS {200}")
            self.assertEqual(response.status_code, 200) 
        except Exception as e:
            self.log.error(e)
            raise e
        result = response.json()["result"]
        self.log.info(f"RESPONSE JSON: \n {result}")
        self.assertEqual(result["name"], "unit_test_vfolder") 
        self.assertTrue("global_entity_id" in result) 
        self.virtual_folder_geids.append(result["global_entity_id"])
        # self.virtual_folder_ids.append(result["id"])

    @unittest.skip("broken")
    def test_02_get_vfolders(self):
        self.log.info("\n")
        self.log.info('02'+'test get collection'.center(80, '-'))
        params = {
            "project_geid": self.container_geid,
            "order_by": "name",
        }
        try:
            response = self.app.get("/v1/collections/", params=params, headers=self.headers)
            self.log.info(f"POST RESPONSE: {response}")
            self.log.info(f"COMPARING: {response.status_code} VS {200}")
            self.assertEqual(response.status_code, 200)
        except Exception as e:
            self.log.error(e)
            raise e
        result = response.json()["result"]
        self.log.info(f"RESPONSE JSON: \n {result}")
        self.assertEqual(result[0]["properties"]["container_id"], self.container_id) 
        self.assertEqual(result[0]["properties"]["name"], "unit_test_vfolder") 


    def test_04_post_vfolders_duplicate(self):
        self.log.info("\n")
        self.log.info('04'+'test create duplicate collection'.center(80, '-'))
        payload = {
            "name": "unit_test_vfolder_dup",
            "project_geid": self.container_geid,
            "username": self.user["username"]
        }
        try:
            response = self.app.post("/v1/collections/", json=payload, headers=self.headers)
            self.log.info(f"POST RESPONSE: {response}")
            self.log.info(f"COMPARING: {response.status_code} VS {200}")
            result = response.json()["result"]
            self.log.info(f"POST RESPONSE JSON: {result}")
            self.virtual_folder_geids.append(result["global_entity_id"])
            # self.virtual_folder_ids.append(result["id"])
            response = self.app.post("/v1/collections/", json=payload, headers=self.headers)
            self.log.info(f"post again with same payload")
            self.log.info(f"POST RESPONSE: {response}")
            self.log.info(f"COMPARING: {response.status_code} VS {409}")
            self.assertEqual(response.status_code, 409)
        except Exception as e:
            self.log.error(e)
            raise e
        self.assertEqual(response.json()["error_msg"], "Found duplicate folder") 

    def test_05_create_vfolder_admin(self):
        self.log.info("\n")
        self.log.info('05'+'test create collection admin'.center(80, '-'))
        payload = {
            "name": "unit_test_vfolder3",
            "project_geid": self.container_geid,
            "username": self.user["username"]
        }
        header = {}
        header["Authorization"] = self.test.auth()
        try:
            response = self.app.post("/v1/collections/", json=payload, headers=header)
            self.log.info(f"POST RESPONSE: {response}")
            self.log.info(f"COMPARING: {response.status_code} VS {200}")
            self.assertEqual(response.status_code, 200)
        except Exception as e:
            self.log.error(e)
            raise e
        result = response.json()["result"]
        self.log.info(f"POST RESPONSE: {result}")
        self.assertEqual(result["name"], "unit_test_vfolder3") 
        self.assertTrue("global_entity_id" in result) 
        self.virtual_folder_geids.append(result["global_entity_id"])
        # self.virtual_folder_ids.append(result["id"])

    def test_06_bulk_update(self):
        self.log.info("\n")
        self.log.info('06'+'test update collection'.center(80, '-'))
        payload = {
            "collections": [
                 {
                    "name": "unit_test_vfolder2",
                    "geid": self.virtual_folder_geids[0],
                },
            ],
            "username": self.user["username"]
        }
        try:
            response = self.app.put("/v1/collections/", json=payload, headers=self.headers)
            self.log.info(f"POST RESPONSE: {response}")
            self.log.info(f"COMPARING: {response.status_code} VS {200}")
            self.assertEqual(response.status_code, 200)
        except Exception as e:
            self.log.error(e)
            raise e
        results = response.json()["result"]
        self.log.info(f"PUT RESPONSE {results}")
        self.assertEqual(results[0]["global_entity_id"], self.virtual_folder_geids[0]) 

    def test_08_bulk_update_missing_attr(self):
        self.log.info("\n")
        self.log.info('08'+'test update collection that lack of attribute'.center(80, '-'))
        payload = {
            "collections": [
                 {
                    "name": "unit_test_vfolder2",
                    #"geid": self.virtual_folder_geids[0],
                },
            ],
            "username": self.user["username"]
        }
        headers = {}
        headers["Authorization"] = self.test.auth()
        try:
            response = self.app.put("/v1/collections/", json=payload, headers=headers)
            self.log.info(f"POST RESPONSE: {response}")
            self.log.info(f"COMPARING: {response.status_code} VS {400}")
            self.assertEqual(response.status_code, 400) 
        except Exception as e:
            self.log.error(e)
            raise e
        results = response.json()["result"]
        self.log.info(f"PUT results: {results}")
        self.assertEqual(response.json()["error_msg"], "Missing required attribute geid") 

    def test_09_bulk_update_admin(self):
        self.log.info("\n")
        self.log.info('09'+'test update collection admin'.center(80, '-'))
        payload = {
            "collections": [
                 {
                    "name": "unit_test_vfolder4",
                    "geid": self.virtual_folder_geids[2],
                },
            ],
            "username": self.user["username"]
        }
        headers = {}
        headers["Authorization"] = self.test.auth()
        try:
            response = self.app.put("/v1/collections/", json=payload, headers=headers)
            self.log.info(f"POST RESPONSE: {response}")
            self.log.info(f"COMPARING: {response.status_code} VS {200}")
            self.assertEqual(response.status_code, 200) 
        except Exception as e:
            self.log.error(e)
            raise e
        results = response.json()["result"]
        self.assertEqual(results[0]["global_entity_id"], self.virtual_folder_geids[2]) 
