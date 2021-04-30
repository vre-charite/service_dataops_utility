import requests
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app import app
from config import ConfigClass
from resources.geid_shortcut import fetch_geid
import os

class SetUpTest:
    def __init__(self, log):
        self.log = log
        self.app = self.create_test_client()

    def create_test_client(self):
        client = TestClient(app)
        return client

    def auth(self, payload=None):
        if not payload:
            payload = {
                "username": "admin",
                "password": "admin",
                "realm": "vre"
            }
        response = requests.post(ConfigClass.AUTH_SERVICE + "users/auth", json=payload)
        data = response.json()
        self.log.info(data)
        return data["result"].get("access_token")

    def auth_member(self, payload=None):
        if not payload:
            payload = {
                "username": "jzhang10",
                "password": "CMDvrecli2021!",
                "realm": "vre"
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

    def create_project(self, code, discoverable='true'):
        self.log.info("\n")
        self.log.info("Preparing testing project".ljust(80, '-'))
        testing_api = ConfigClass.NEO4J_HOST + "/v1/neo4j/nodes/Dataset"
        params = {"name": "DataopsUTUnitTest",
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

    def delete_node(self, label, node_id):
        self.log.info("\n")
        self.log.info("Preparing delete node".ljust(80, '-'))
        delete_api = ConfigClass.NEO4J_HOST + f"/v1/neo4j/nodes/{label}/node/{node_id}"
        try:
            self.log.info(f"DELETE Project: {node_id}")
            delete_res = requests.delete(delete_api)
            self.log.info(f"DELETE STATUS: {delete_res.status_code}")
            self.log.info(f"DELETE RESPONSE: {delete_res.text}")
        except Exception as e:
            self.log.info(f"ERROR DELETING PROJECT: {e}")
            self.log.info(f"PLEASE DELETE THE PROJECT MANUALLY WITH ID: {node_id}")
            raise e
