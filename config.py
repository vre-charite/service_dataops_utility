import os
import requests
from requests.models import HTTPError
# os.environ['env'] = "test"

srv_namespace = "service_dataops_utility"
CONFIG_CENTER = "http://10.3.7.222:5062" \
    if os.environ.get('env', "test") == "test" \
    else "http://common.utility:5062"


def vault_factory() -> dict:
    url = CONFIG_CENTER + \
        "/v1/utility/config/{}".format(srv_namespace)
    config_center_respon = requests.get(url)
    if config_center_respon.status_code != 200:
        raise HTTPError(config_center_respon.text)
    return config_center_respon.json()['result']


class ConfigClass(object):
    vault = vault_factory()
    env = os.environ.get('env')
    disk_namespace = os.environ.get('namespace')
    version = "0.1.0"
    VRE_ROOT_PATH = "/vre-data"
    AUTH_SERVICE = vault['AUTH_SERVICE']+'/v1/'
    NEO4J_SERVICE = vault['NEO4J_SERVICE']+"/v1/neo4j/"
    NEO4J_SERVICE_V2 = vault['NEO4J_SERVICE']+"/v2/neo4j/"
    ENTITYINFO_SERVICE = vault['ENTITYINFO_SERVICE']+"/v1/"
    CATALOGUING_SERVICE_V2 = vault['CATALOGUING_SERVICE']+"/v2/"
    QUEUE_SERVICE = vault['QUEUE_SERVICE']+"/v1/"
    # DATA_OPS_GR = vault['DATA_OPS_GR']
    UTILITY_SERVICE = vault['UTILITY_SERVICE']
    SEND_MESSAGE_URL = vault['SEND_MESSAGE_URL']+"/v1/send_message"
    PROVENANCE_SERVICE = vault['PROVENANCE_SERVICE']+"/v1/"
    MINIO_SERVICE = "http://" + vault['MINIO_ENDPOINT']
    DATA_UPLOAD_SERVICE_GREENROOM = vault['DATA_UPLOAD_SERVICE_GREENROOM']+"/v1"
    # Redis Service
    REDIS_HOST = vault['REDIS_HOST']
    REDIS_PORT = int(vault['REDIS_PORT'])
    REDIS_DB = int(vault['REDIS_DB'])
    REDIS_PASSWORD = vault['REDIS_PASSWORD']
    # disk mounts
    ROOT_PATH = {
        "vre": "/vre-data",
        "greenroom": "/data/vre-storage"
    }.get(os.environ.get('namespace'), "./test_project")
    NFS_ROOT_PATH = "/data/vre-storage"

    RDS_HOST = vault['RDS_HOST']
    RDS_PORT = vault['RDS_PORT']
    RDS_DBNAME = vault['RDS_DBNAME']
    RDS_USER = vault['RDS_USER']
    RDS_PWD = vault['RDS_PWD']
    RDS_SCHEMA_DEFAULT = vault['RDS_SCHEMA_DEFAULT']
    SQLALCHEMY_DATABASE_URI = f"postgresql://{RDS_USER}:{RDS_PWD}@{RDS_HOST}/{RDS_DBNAME}"


