from redis import StrictRedis
from config import ConfigClass
from enum import Enum
import json
from datetime import timedelta

from commons.logger_services.logger_factory_service import SrvLoggerFactory

_logger = SrvLoggerFactory('SrvRedisSingleton').get_logger()

class SrvRedisSingleton():

    __instance = {}

    def __init__(self):
        self.host = ConfigClass.REDIS_HOST
        self.port = ConfigClass.REDIS_PORT
        self.db = ConfigClass.REDIS_DB
        self.pwd = ConfigClass.REDIS_PASSWORD
        self.connect()

    def connect(self):
        if self.__instance:
            pass
        else:
            self.__instance = StrictRedis(host=self.host,
                port=self.port,
                db=self.db,
                password=self.pwd)

    def get_by_key(self, key: str):
        return self.__instance.get(key)

    def set_by_key(self, key: str, content: str):
        res = self.__instance.set(key, content, ex=timedelta(hours=24))
        return res
        # _logger.debug(key + ":  " + content)

    def mget_by_prefix(self, prefix: str):
        # _logger.debug(prefix)
        query = '{}:*'.format(prefix)
        keys = self.__instance.keys(query)
        return self.__instance.mget(keys)

    def check_by_key(self, key: str):
        return self.__instance.exists(key)

    def delete_by_key(self, key: str):
        return self.__instance.delete(key)

    def unlink_by_key(self, key: str):
        return self.__instance.unlink(key)

    def mdele_by_prefix(self, prefix: str):
        # _logger.debug(prefix)
        query = '{}:*'.format(prefix)
        keys = self.__instance.keys(query)
        results = []
        for key in keys:
            res = self.delete_by_key(key)
            results.append(res)
        return results

    def get_by_pattern(self, key: str, pattern: str):
        query_string = '{}:*{}*'.format(key, pattern)
        keys = self.__instance.keys(query_string)
        return self.__instance.mget(keys)

    def publish(self, channel, data):
        res = self.__instance.publish(channel, data)
        return res
    
    def subscriber(self, channel):
        p = self.__instance.pubsub()
        p.subscribe(channel)
        return p

    def file_get_status(self, file_path):
        query = '*:{}'.format(file_path)
        keys = self.__instance.keys(query)
        result = self.__instance.mget(keys)

        current_action = None

        decoded_result = []
        for record in result:
            record = record.decode('utf-8')
            info = json.loads(record)
            decoded_result.append(info)

        if len(decoded_result) > 0:
            latest_item = max(decoded_result, key=lambda x:x['update_timestamp'])

            if latest_item['status'] == 'SUCCEED' or latest_item['status'] == 'TERMINATED':
                return current_action
            else:
                return latest_item['action']

        return current_action 


class ERedisChannels(Enum):
    pipeline_process_start = 0