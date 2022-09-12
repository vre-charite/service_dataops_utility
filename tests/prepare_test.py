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

import requests
from fastapi.testclient import TestClient

from app import create_app
from config import ConfigClass
from resources.helpers import fetch_geid


class SetUpTest:
    def __init__(self, log):
        self.log = log
        self.app = self.create_test_client()

    def create_test_client(self):
        client = TestClient(create_app())
        return client

    def auth(self, payload=None):
        if not payload:
            payload = {
                "username": "admin",
                "password": "admin",
                "realm": ""
            }
        response = requests.post(ConfigClass.AUTH_SERVICE + "users/auth", json=payload)
        data = response.json()
        self.log.info(data)
        return data["result"].get("access_token")

    def auth_member(self, payload=None):
        if not payload:
            payload = {
                "username": "admin",
                "password": "admin",
                "realm": ""
            }
        response = requests.post(ConfigClass.AUTH_SERVICE + "users/auth", json=payload)
        data = response.json()
        self.log.info(data)
        return data["result"].get("access_token")

    def get_user(self):
        payload = {
            "name": "jzhang10",
        }
        response = requests.post(ConfigClass.NEO4J_SERVICE + "nodes/User/query", json=payload)
        self.log.info(response.json())
        return response.json()[0]


    def add_user_to_project(self, user_id, project_id, role):
        payload = {
            "start_id": user_id,
            "end_id": project_id,
        }
        response = requests.post(ConfigClass.NEO4J_SERVICE + f"relations/{role}", json=payload)
        if response.status_code != 200:
            raise Exception(f"Error adding user to project: {response.json()}")

    def remove_user_from_project(self, user_id, project_id):
        payload = {
            "start_id": user_id,
            "end_id": project_id,
        }
        response = requests.delete(ConfigClass.NEO4J_SERVICE + "relations", params=payload)
        if response.status_code != 200:
            raise Exception(f"Error removing user from project: {response.json()}")

    def create_project(self, code, discoverable='true', name="DataopsUTUnitTest"):
        self.log.info("\n")
        self.log.info("Preparing testing project".ljust(80, '-'))
        testing_api = ConfigClass.NEO4J_SERVICE + "nodes/Container"
        params = {"name": name,
                  "path": code,
                  "code": code,
                  "description": "Project created by unit test, will be deleted soon...",
                  "discoverable": discoverable,
                  "type": "Usecase",
                  "tags": ['test'],
                  "global_entity_id": fetch_geid()
                  }
        self.log.info(f"POST API: {testing_api}")
        self.log.info(f"POST params: {params}")
        try:
            res = requests.post(testing_api, json=params)
            self.log.info(f"RESPONSE DATA: {res.text}")
            self.log.info(f"RESPONSE STATUS: {res.status_code}")
            assert res.status_code == 200
            node = res.json()[0]
            return node
        except Exception as e:
            self.log.info(f"ERROR CREATING PROJECT: {e}")
            raise e

    def delete_node(self, label, input_nodeid):
        self.log.info("\n")
        self.log.info("Preparing delete node".ljust(80, '-'))
        if label == "VirtualFolder":
            node_id = self.get_id(label, input_nodeid)
        else:
            node_id = input_nodeid
        if node_id is None:
            self.log.info(f"GET NODE ID FAIL: node_geid {input_nodeid}")
        delete_api = ConfigClass.NEO4J_SERVICE + f"nodes/{label}/node/{node_id}"
        try:
            self.log.info(f"DELETE Project: {node_id}")
            delete_res = requests.delete(delete_api)
            self.log.info(f"DELETE STATUS: {delete_res.status_code}")
            self.log.info(f"DELETE RESPONSE: {delete_res.text}")
        except Exception as e:
            self.log.info(f"ERROR DELETING PROJECT: {e}")
            self.log.info(f"PLEASE DELETE THE PROJECT MANUALLY WITH ID: {node_id}")
            raise e

    def get_id(self, label, node_geid):
        url = ConfigClass.NEO4J_SERVICE + f"nodes/{label}/query"
        payload = {
            "global_entity_id": node_geid
        }
        result = requests.post(url, json = payload)
        if result.status_code != 200 or result.json() == []:
            return None
        result = result.json()[0]
        node_id = result["id"]
        return node_id

    def get_project_details(self, project_code):
        try:
            url = ConfigClass.NEO4J_SERVICE + "nodes/Container/query"
            response = requests.post(url, json={"code":project_code})
            if response.status_code == 200:
                response = response.json()
                return response
        except Exception as error:
            self.log.info(f"ERROR WHILE GETTING PROJECT: {error}")
            raise error

    def get_folder_details(self, folder_name):
        try:
            url = ConfigClass.NEO4J_SERVICE + "nodes/Folder/query"
            response = requests.post(url, json={"name":folder_name})
            if response.status_code == 200:
                response = response.json()
                return response
        except Exception as error:
            self.log.info(f"ERROR WHILE GETTING PROJECT: {error}")
            raise error

    def delete_folder_node(self, node_id):
        self.log.info("\n")
        self.log.info("Preparing delete folder node".ljust(80, '-'))
        delete_api = ConfigClass.NEO4J_SERVICE + "nodes/Folder/node/%s" % str(node_id)
        try:
            delete_res = requests.delete(delete_api)
            self.log.info(f"DELETE STATUS: {delete_res.status_code}")
            self.log.info(f"DELETE RESPONSE: {delete_res.text}")
        except Exception as e:
            self.log.info(f"ERROR DELETING FILE: {e}")
            self.log.info(f"PLEASE DELETE THE FILE MANUALLY WITH ID: {node_id}")
            raise e
