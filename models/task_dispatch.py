from pydantic import BaseModel, validator, Field, root_validator
from models.base_models import APIResponse

class TaskDispatchPOST(BaseModel):
    session_id: str
    task_id: str
    job_id: str
    source: str
    action: str
    target_status: str
    project_code: str
    operator: str
    progress: int = 0
    payload: dict = {}


class TaskDispatchPOSTResponse(APIResponse):
    result: dict = Field({}, example={
        "session_id": "unique_session_2021",
        "task_id": "task1",
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
    }
    )

class TaskDispatchDELETE(BaseModel):
    session_id: str
    job_id: str = "*"
    action: str = "*"
    project_code: str = "*"
    operator: str = "*"

class TaskDispatchPUT(BaseModel):
    session_id: str
    job_id: str
    status: str
    add_payload: dict = {}
    progress: int = 0