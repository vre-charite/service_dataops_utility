from enum import Enum
from typing import List
from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from pydantic import Extra
from pydantic import Field

from models.base_models import APIResponse


class FileOperationTarget(BaseModel):
    """Validate structure of single target in file operation payload."""

    geid: str

    class Config:
        extra = Extra.ignore


class FileOperationPayload(BaseModel):
    """Validate structure of payload in file operation post body."""

    request_id: Optional[UUID]
    targets: List[FileOperationTarget]

    class Config:
        extra = Extra.allow


class FileOperationsPOST(BaseModel):
    session_id: str
    task_id: str = "default_task_id"  # a geid to mark a batch of operations
    payload: FileOperationPayload
    operator: str
    operation: str = "copy/delete"
    project_geid: str


class FileOperationsPOSTResponse(APIResponse):
    result: dict = Field({}, example=[
        {
            "session_id": "unique_session_2021",
            "job_id": "1bfe8fd8-8b41-11eb-a8bd-eaff9e667817-1616439732",
            "source": "file1.png",
            "action": "data_transfer",
            "status": "PENDING",
            "project_code": "gregtest",
            "operator": "zhengyang",
            "progress": 0,
            "payload": {
            },
            "update_timestamp": "1616439731"
        },
        {
            "session_id": "unique_session_2021",
            "job_id": "1c90ceac-8b41-11eb-bf7a-eaff9e667817-1616439733",
            "source": "a/b/file1.png",
            "action": "data_upload",
            "status": "SUCCEED",
            "project_code": "gregtest",
            "operator": "zhengyang",
            "progress": 0,
            "payload": {
            },
            "update_timestamp": "1616439732"
        }
    ]
    )


class FileOperationsValidatePOST(BaseModel):
    payload: dict = {}
    operator: str
    operation: str = "copy/delete"
    project_geid: str


class EActionState(Enum):
    """Action state."""

    INIT = 0,
    PRE_UPLOADED = 1,
    CHUNK_UPLOADED = 2,
    FINALIZED = 3,
    SUCCEED = 4,
    TERMINATED = 5
    RUNNING = 6
    ZIPPING = 7
    READY_FOR_DOWNLOADING = 8


class MessageHubPOST(BaseModel):
    message: str
    channel: str


class MessageHubPOSTResponse(APIResponse):
    result: dict = Field({}, example="succeed")
