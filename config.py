import os
import requests
from requests.models import HTTPError
from pydantic import BaseSettings, Extra
from typing import Dict, Set, List, Any
from functools import lru_cache

SRV_NAMESPACE = os.environ.get("APP_NAME", "service_dataops_utility")
CONFIG_CENTER_ENABLED = os.environ.get("CONFIG_CENTER_ENABLED", "false")
CONFIG_CENTER_BASE_URL = os.environ.get("CONFIG_CENTER_BASE_URL", "NOT_SET")

def load_vault_settings(settings: BaseSettings) -> Dict[str, Any]:
    if CONFIG_CENTER_ENABLED == "false":
        return {}
    else:
        return vault_factory(CONFIG_CENTER_BASE_URL)

def vault_factory(config_center) -> dict:
    url = f"{config_center}/v1/utility/config/{SRV_NAMESPACE}"
    config_center_respon = requests.get(url)
    if config_center_respon.status_code != 200:
        raise HTTPError(config_center_respon.text)
    return config_center_respon.json()['result']


class Settings(BaseSettings):
    port: int = 5063
    host: str = "127.0.0.1"
    env: str = ""
    namespace: str = ""

    VRE_ROOT_PATH: str = "/vre-data"
    AUTH_SERVICE: str
    NEO4J_SERVICE: str
    ENTITYINFO_SERVICE: str
    CATALOGUING_SERVICE: str
    QUEUE_SERVICE: str
    UTILITY_SERVICE: str
    SEND_MESSAGE_URL: str
    PROVENANCE_SERVICE: str
    MINIO_ENDPOINT: str
    DATA_UPLOAD_SERVICE_GREENROOM: str
    # Redis Service
    REDIS_HOST: str
    REDIS_PORT: str
    REDIS_DB: str
    REDIS_PASSWORD: str
    # disk mounts
    ROOT_PATH: str = {
        "vre": "/vre-data",
        "greenroom": "/data/vre-storage"
    }.get(os.environ.get('namespace'), "./test_project")
    NFS_ROOT_PATH: str = "/data/vre-storage"

    RDS_HOST: str
    RDS_PORT: str
    RDS_DBNAME: str
    RDS_USER: str
    RDS_PWD: str
    RDS_SCHEMA_DEFAULT: str

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = Extra.allow

        @classmethod
        def customise_sources(
            cls,
            init_settings,
            env_settings,
            file_secret_settings,
        ):
            return (
                load_vault_settings,
                env_settings,
                init_settings,
                file_secret_settings,
            )
    

@lru_cache(1)
def get_settings():
    settings =  Settings()
    return settings

class ConfigClass(object):
    settings = get_settings()

    version = "0.1.0"
    env = settings.env
    disk_namespace = settings.namespace

    VRE_ROOT_PATH = "/vre-data"
    AUTH_SERVICE = settings.AUTH_SERVICE + '/v1/'
    NEO4J_SERVICE = settings.NEO4J_SERVICE + "/v1/neo4j/"
    NEO4J_SERVICE_V2 = settings.NEO4J_SERVICE + "/v2/neo4j/"
    ENTITYINFO_SERVICE = settings.ENTITYINFO_SERVICE + "/v1/"
    CATALOGUING_SERVICE_V2 = settings.CATALOGUING_SERVICE + "/v2/"
    QUEUE_SERVICE = settings.QUEUE_SERVICE + "/v1/"
    UTILITY_SERVICE = settings.UTILITY_SERVICE
    SEND_MESSAGE_URL = settings.SEND_MESSAGE_URL + "/v1/send_message"
    PROVENANCE_SERVICE = settings.PROVENANCE_SERVICE + "/v1/"
    MINIO_SERVICE = "http://" + settings.MINIO_ENDPOINT
    DATA_UPLOAD_SERVICE_GREENROOM = settings.DATA_UPLOAD_SERVICE_GREENROOM + "/v1"
    # Redis Service
    REDIS_HOST = settings.REDIS_HOST
    REDIS_PORT = int(settings.REDIS_PORT)
    REDIS_DB = int(settings.REDIS_DB)
    REDIS_PASSWORD = settings.REDIS_PASSWORD
    # disk mounts
    ROOT_PATH = settings.ROOT_PATH
    NFS_ROOT_PATH = settings.NFS_ROOT_PATH

    RDS_HOST = settings.RDS_HOST
    RDS_PORT = settings.RDS_PORT
    RDS_DBNAME = settings.RDS_DBNAME
    RDS_USER = settings.RDS_USER
    RDS_PWD = settings.RDS_PWD
    RDS_SCHEMA_DEFAULT = settings.RDS_SCHEMA_DEFAULT
    SQLALCHEMY_DATABASE_URI = f"postgresql://{RDS_USER}:{RDS_PWD}@{RDS_HOST}/{RDS_DBNAME}"



    