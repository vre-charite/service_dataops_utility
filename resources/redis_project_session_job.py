# Copyright 2022 Indoc Research
# 
# Licensed under the EUPL, Version 1.2 or – as soon they
# will be approved by the European Commission - subsequent
# versions of the EUPL (the "Licence");
# You may not use this work except in compliance with the
# Licence.
# You may obtain a copy of the Licence at:
# 
# https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12
# 
# Unless required by applicable law or agreed to in
# writing, software distributed under the Licence is
# distributed on an "AS IS" basis,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied.
# See the Licence for the specific language governing
# permissions and limitations under the Licence.
# 

import json
import time

from resources.redis import SrvAioRedisSingleton


class SessionJob:
    """Session Job ORM."""

    def __init__(self, session_id, code, action, operator, job_id=None, label='Container', task_id='default_task'):
        """Init function, if provide job_id, will read from redis.

        If not provide, create a new job, and need to call set_job_id first, label can be Dataset or Container(Project)
        """

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

    @classmethod
    async def load(cls, session_id, code, action, operator, job_id=None, label='Container', task_id='default_task'):
        instance = cls(session_id, code, action, operator, job_id, label, task_id)
        await instance.read()
        return instance

    def to_dict(self):
        return {
            'session_id': self.session_id,
            'task_id': self.task_id,
            'job_id': self.job_id,
            'label': self.label,
            'code': self.code,
            'action': self.action,
            'operator': self.operator,
            'source': self.source,
            'status': self.status,
            'progress': self.progress,
            'payload': self.payload,
        }

    async def set_job_id(self, job_id):
        """Set job id."""

        self.job_id = job_id
        await self.check_job_id()

    def set_source(self, source: str):
        """Set job source."""

        self.source = source

    def add_payload(self, key: str, value):
        """Will update if exists the same key."""

        self.payload[key] = value

    def set_status(self, status: str):
        """Set job status."""

        self.status = status

    def set_progress(self, progress: int):
        """Set job progress."""

        self.progress = progress

    async def save(self):
        """Save in redis."""

        if not self.job_id:
            raise Exception('[SessionJob] job_id not provided')
        if not self.source:
            raise Exception('[SessionJob] source not provided')
        if not self.status:
            raise Exception('[SessionJob] status not provided')
        return await session_job_set_status(
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
            self.progress,
        )

    async def read(self):
        """Read from redis."""
        fetched = await session_job_get_status(
            self.session_id, self.label, self.job_id, self.code, self.action, self.operator
        )
        if not fetched:
            raise Exception('[SessionJob] Not found job: {}'.format(self.job_id))
        job_read = fetched[0]
        self.source = job_read['source']
        self.status = job_read['status']
        self.progress = job_read['progress']
        self.payload = job_read['payload']
        self.task_id = job_read['task_id']
        self.action = job_read['action']
        self.operator = job_read['operator']
        self.code = job_read['code']

    async def check_job_id(self):
        """Check if job_id already been used."""

        fetched = await session_job_get_status(
            self.session_id, self.label, self.job_id, self.code, self.action, self.operator
        )
        if fetched:
            raise Exception('[SessionJob] job id already exists: {}'.format(self.job_id))


async def session_job_set_status(
    session_id, label, task_id, job_id, source, action, target_status, code, operator, payload=None, progress=0
):
    """Set session job status."""
    srv_redis = SrvAioRedisSingleton()
    my_key = 'dataaction:{}:{}:{}:{}:{}:{}:{}'.format(session_id, label, job_id, action, code, operator, source)
    record = {
        'session_id': session_id,
        'label': label,
        'task_id': task_id,
        'job_id': job_id,
        'source': source,
        'action': action,
        'status': target_status,
        'code': code,
        'operator': operator,
        'progress': progress,
        'payload': payload,
        'update_timestamp': str(round(time.time())),
    }
    my_value = json.dumps(record)
    await srv_redis.set_by_key(my_key, my_value)
    return record


async def session_job_get_status(session_id, label='Container', job_id='*', code='*', action='*', operator='*'):
    srv_redis = SrvAioRedisSingleton()
    my_key = 'dataaction:{}:{}:{}:{}:{}:{}'.format(session_id, label, job_id, action, code, operator)
    res_binary = await srv_redis.mget_by_prefix(my_key)
    return [json.loads(record.decode('utf-8')) for record in res_binary] if res_binary else []


async def session_job_delete_status(session_id, label='Container', job_id='*', code='*', action='*', operator='*'):
    srv_redis = SrvAioRedisSingleton()
    my_key = 'dataaction:{}:{}:{}:{}:{}:{}'.format(session_id, label, job_id, action, code, operator)
    res_binary_list = await srv_redis.mdele_by_prefix(my_key)
    return res_binary_list
