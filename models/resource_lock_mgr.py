import requests
from commons.data_providers.redis import SrvRedisSingleton
from enum import Enum
import json

class EResourceLockStatus(Enum):
    LOCKED=10
    UNLOCKED=20

class ResourceLockManager:

    def __init__(self):
        self.__srv_redis = SrvRedisSingleton()

    def lock(self, key, sub_key):
        lock_key = "RLOCK:{}:{}".format(key, sub_key)
        self.__srv_redis.set_by_key(lock_key, EResourceLockStatus.LOCKED.name)

    def unlock(self, key, sub_key):
        lock_key = "RLOCK:{}:{}".format(key, sub_key)
        self.__srv_redis.delete_by_key(lock_key)
    
    def unlink(self, key, sub_key):
        lock_key = "RLOCK:{}:{}".format(key, sub_key)
        self.__srv_redis.unlink_by_key(lock_key)

    def check_lock(self, key, sub_key):
        lock_key = "RLOCK:{}:{}".format(key, sub_key)
        record = self.__srv_redis.get_by_key(lock_key)
        if record:
            record = record.decode('utf-8')
            return record
        else:
            return None

    def clear_all(self):
        lock_key = "RLOCK"
        self.__srv_redis.mdele_by_prefix(lock_key)
