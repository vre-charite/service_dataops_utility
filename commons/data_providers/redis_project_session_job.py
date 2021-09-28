import time
import json
from .redis import SrvRedisSingleton


class SessionJob:
    '''
    Session Job ORM
    '''

    def __init__(self, session_id, code, action, operator, job_id=None, \
        label="Container", task_id="default_task"):
        '''
        Init function, if provide job_id, will read from redis.
        If not provide, create a new job, and need to call set_job_id first,
        label can be Dataset or Container(Project)
        '''
        self.session_id = session_id
        self.label = label
        self.task_id = task_id
        self.job_id = job_id
        self.code = code
        self.action = action
        self.operator = operator
        self.source = None
        self.status = None
        self.progress = 0
        self.payload = {}
        if job_id:
            self.read()

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "task_id": self.task_id,
            "job_id": self.job_id,
            "label": self.label,
            "code": self.code,
            "action": self.action,
            "operator": self.operator,
            "source": self.source,
            "status": self.status,
            "progress": self.progress,
            "payload": self.payload
        }

    def set_job_id(self, job_id):
        '''
        set job id
        '''
        self.job_id = job_id
        self.check_job_id()

    def set_source(self, source: str):
        '''
        set job source
        '''
        self.source = source

    def add_payload(self, key: str, value):
        '''
        will update if exists the same key
        '''
        self.payload[key] = value

    def set_status(self, status: str):
        '''
        set job status
        '''
        self.status = status

    def set_progress(self, progress: int):
        '''
        set job status
        '''
        self.progress = progress

    def save(self):
        '''
        save in redis
        '''
        if not self.job_id:
            raise(Exception('[SessionJob] job_id not provided'))
        if not self.source:
            raise(Exception('[SessionJob] source not provided'))
        if not self.status:
            raise(Exception('[SessionJob] status not provided'))
        return session_job_set_status(
            self.session_id,
            self.label,
            self.task_id,
            self.job_id,
            self.source,
            self.action,
            self.status,
            self.code,
            self.operator,
            self.payload,
            self.progress
        )

    def read(self):
        '''
        read from redis
        '''
        fetched = session_job_get_status(
            self.session_id,
            self.label,
            self.job_id,
            self.code,
            self.action,
            self.operator
        )
        if not fetched:
            raise Exception(
                '[SessionJob] Not found job: {}'.format(self.job_id))
        job_read = fetched[0]
        self.source = job_read['source']
        self.status = job_read['status']
        self.progress = job_read['progress']
        self.payload = job_read['payload']
        self.task_id = job_read['task_id']
        self.action = job_read['action']
        self.operator = job_read['operator']
        self.code = job_read['code']

    def check_job_id(self):
        '''
        check if job_id already been used
        '''
        fetched = session_job_get_status(
            self.session_id,
            self.label,
            self.job_id,
            self.code,
            self.action,
            self.operator
        )
        if fetched:
            raise Exception(
                '[SessionJob] job id already exists: {}'.format(self.job_id))


def session_job_set_status(session_id, label, task_id, job_id, source, action, target_status,
                           code, operator, payload=None, progress=0):
    '''
    set session job status
    '''
    srv_redis = SrvRedisSingleton()
    my_key = "dataaction:{}:{}:{}:{}:{}:{}:{}".format(
        session_id, label, job_id, action, code, operator, source)
    record = {
        "session_id": session_id,
        "label": label,
        "task_id": task_id,
        "job_id": job_id,
        "source": source,
        "action": action,
        "status": target_status,
        "code": code,
        "operator": operator,
        "progress": progress,
        "payload": payload,
        'update_timestamp': str(round(time.time()))
    }
    my_value = json.dumps(record)
    res = srv_redis.set_by_key(my_key, my_value)
    return record


def session_job_get_status(session_id, label="Container", job_id="*", code="*", action="*", operator="*"):
    srv_redis = SrvRedisSingleton()
    my_key = "dataaction:{}:{}:{}:{}:{}:{}".format(
        session_id, label, job_id, action, code, operator)
    res_binary = srv_redis.mget_by_prefix(my_key)
    return [json.loads(record.decode('utf-8')) for record in res_binary] if res_binary else []


def session_job_delete_status(session_id, label="Container", job_id="*", code="*", action="*", operator="*"):
    srv_redis = SrvRedisSingleton()
    my_key = "dataaction:{}:{}:{}:{}:{}:{}".format(
        session_id, label, job_id, action, code, operator)
    res_binary_list = srv_redis.mdele_by_prefix(my_key)
    return res_binary_list
