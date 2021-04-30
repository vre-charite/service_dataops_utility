import os

class ConfigClass(object):
    env = os.environ.get('env')

    VRE_ROOT_PATH = "/vre-data"
    NEO4J_SERVICE = "http://neo4j.utility:5062/v1/neo4j/"
    NEO4J_HOST = "http://neo4j.utility:5062"
    FILEINFO_HOST = "http://entityinfo.utility:5066"
    METADATA_API = "http://cataloguing.utility:5064"
    SEND_MESSAGE_URL = "http://queue-producer.greenroom:6060/v1/send_message"
    DATA_OPS_GR = "http://dataops-gr.greenroom:5063"
    # utility service
    UTILITY_SERVICE = "http://common.utility:5062"
    # SEND_MESSAGE_URL = "http://10.3.7.214:6060/v1/send_message"
    if env == "test":
        NEO4J_HOST = "http://10.3.7.216:5062"
        NEO4J_SERVICE = "http://10.3.7.216:5062/v1/neo4j/"
        UTILITY_SERVICE = "http://10.3.7.222:5062"
        AUTH_SERVICE = "http://10.3.7.217:5061/v1/"


    # disk mounts
    NFS_ROOT_PATH = "/data/vre-storage"
    VRE_ROOT_PATH = "/vre-data"
