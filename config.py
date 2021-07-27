import os
# os.environ['env'] = "test"


class ConfigClass(object):
    env = os.environ.get('env', "test")

    VRE_ROOT_PATH = "/vre-data"
    NEO4J_SERVICE = "http://neo4j.utility:5062/v1/neo4j/"
    NEO4J_SERVICE_V2  = "http://neo4j.utility:5062/v2/neo4j/"
    ENTITYINFO_SERVICE = "http://entityinfo.utility:5066/v1/"
    CATALOGUING_SERVICE_V2 = "http://cataloguing.utility:5064/v2/"
    QUEUE_SERVICE = "http://queue-producer.greenroom:6060/v1/"
    DATA_OPS_GR = "http://dataops-gr.greenroom:5063"
    UTILITY_SERVICE = "http://common.utility:5062"
    SEND_MESSAGE_URL = "http://queue-producer.greenroom:6060/v1/send_message"
    PROVENANCE_SERVICE = "http://provenance.utility:5077/v1/"
    DATA_UPLOAD_SERVICE_GREENROOM = "http://upload.greenroom:5079/v1"

    MINIO_SERVICE = "http://minio.minio:9000"
    if env == "test":
        MINIO_SERVICE = "http://10.3.7.220"


    # disk mounts
    NFS_ROOT_PATH = "/data/vre-storage"

    # Job status related
    # Redis Service
    REDIS_HOST = "redis-master.utility"
    REDIS_PORT = 6379
    REDIS_DB = 0
    REDIS_PASSWORD = {
        'staging': '8EH6QmEYJN',
        'charite': 'o2x7vGQx6m'
    }.get(env, "5wCCMMC1Lk")

    if env == "test":
        REDIS_HOST = "10.3.7.233"
        NEO4J_SERVICE = "http://10.3.7.216:5062/v1/neo4j/"
        NEO4J_SERVICE_V2 = "http://10.3.7.216:5062/v2/neo4j/"
        UTILITY_SERVICE = "http://10.3.7.222:5062"
        AUTH_SERVICE = "http://10.3.7.217:5061/v1/"
        QUEUE_SERVICE = "http://10.3.7.214:6060/v1/"
        SEND_MESSAGE_URL = "http://10.3.7.214:6060/v1/send_message"
        PROVENANCE_SERVICE = "http://10.3.7.202:5077/v1/"
        DATA_UPLOAD_SERVICE_GREENROOM = "http://10.3.7.201:5079/v1"

# disk mounts
    ROOT_PATH = {
        "vre": "/vre-data",
        "greenroom": "/data/vre-storage"
    }.get(os.environ.get('namespace'), "./test_project")
