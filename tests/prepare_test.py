import requests
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app import app
from config import ConfigClass

class SetupTest:
    def __init__(self, log):
        self.log = log
        self.client = TestClient(app)
        self.log.info("Test Start")
