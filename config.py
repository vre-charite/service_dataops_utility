import os

class ConfigClass(object):
    env = os.environ.get('env', 'test')

    VRE_ROOT_PATH = "/vre-data"
    NEO4J_SERVICE = "http://neo4j.utility:5062/v1/neo4j/"
    NEO4J_SERVICE_V2  = "http://neo4j.utility:5062/v2/neo4j/"
    ENTITYINFO_SERVICE = "http://entityinfo.utility:5066/v1/"
    CATALOGUING_SERVICE_V2 = "http://cataloguing.utility:5064/v2/"
    QUEUE_SERVICE = "http://queue-producer.greenroom:6060/v1/"
    DATA_OPS_GR = "http://dataops-gr.greenroom:5063"
    UTILITY_SERVICE = "http://common.utility:5062"
    SEND_MESSAGE_URL = "http://queue-producer.greenroom:6060/v1/send_message"

    # disk mounts
    NFS_ROOT_PATH = "/data/vre-storage"
    VRE_ROOT_PATH = "/vre-data"

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