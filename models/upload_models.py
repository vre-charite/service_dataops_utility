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

from pydantic import BaseModel, Field
from models.base_models import APIResponse

class TaskModel(BaseModel):
    key: str = ""
    session_id: str = ""
    task_id: str = ""
    start_timestamp: str = ""
    end_timestamp: str = ""
    frontend_state: str = "uploading"
    state: str = "init"
    progress: float = 0.0
    file_name: str = ""
    project_code: str = ""
    project_id: str = ""

class StatusUploadResponse(APIResponse):
    """
    Delete file upload response class
    """
    result: dict = Field({}, example={
        "code": 200,
        "error_msg": "",
        "result": {"Session id deleted:" "admin-a183jcalt13"}
    })
