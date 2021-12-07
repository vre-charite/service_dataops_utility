from pydantic import BaseModel, validator, Field, root_validator
from models.base_models import APIResponse
from enum import Enum

class FileLock(BaseModel):
    resource_key: str # a identity key to mark the locked resource, can be path, geid, guid...
    operation: str

class RLockPOST(BaseModel):
    resource_key: str # a identity key to mark the locked resource, can be path, geid, guid...
    sub_key: str = "default"  # a sub_key

class RLockDELETE(BaseModel):
    resource_key: str # a identity key to mark the locked resource, can be path, geid, guid...
    sub_key: str = "default"  # a sub_key

class RLockResponse(APIResponse):
    result: dict = Field({}, example={
        'key': "str",
        'status': "LOCKED"
    }
    )

class RLockClearResponse(APIResponse):
    result: dict = Field({}, example={
            'key': "all",
            'status': "UNLOCKED"
        }
    )