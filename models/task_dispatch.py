from pydantic import BaseModel, validator, Field, root_validator
from models.base_models import APIResponse

################################################################################
# the payload field description
################################################################################
# - session_id: pass by frontend to record the user login session each time
# normally will be formated as <user_name>-<hash_id>
#
# - task_id: is the high level filter. the task can contain the multiple actions.
# but isnot very often for now. you can set same as the job_id
#
# - job_id: is the basic unit for async job(update/download).
#
# - source: the action item list such as file download list
#
# - action: the file action name such as file_download
#
# - target_status: the status can be following three
#    - RUNNING
#    - FINISH
#    - ERROR
#
# - operator: who take the action
#
# - project code: the unique identifier for project OR dataset
#
# - progress: the optional payload for progress bar
################################################################################

class TaskDispatchPOST(BaseModel):
    session_id: str
    label: str = "Container"
    task_id: str
    job_id: str
    source: str
    action: str
    target_status: str
    code: str
    operator: str
    progress: int = 0
    payload: dict = {}


class TaskDispatchPOSTResponse(APIResponse):
    result: dict = Field({}, example={
        "session_id": "unique_session_2021",
        "label": "Container",
        "task_id": "task1",
        "job_id": "1bfe8fd8-8b41-11eb-a8bd-eaff9e667817-1616439732",
        "source": "file1.png",
        "action": "data_transfer",
        "status": "PENDING",
        "code": "gregtest",
        "operator": "zhengyang",
        "progress": 0,
        "payload": {
        },
        "update_timestamp": "1616439731"
    }
    )

class TaskDispatchDELETE(BaseModel):
    session_id: str
    label: str = "Container"
    job_id: str = "*"
    action: str = "*"
    code: str = "*"
    operator: str = "*"

class TaskDispatchPUT(BaseModel):
    session_id: str
    label: str = "Container"
    job_id: str
    status: str
    add_payload: dict = {}
    progress: int = 0