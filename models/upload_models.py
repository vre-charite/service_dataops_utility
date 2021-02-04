from pydantic import BaseModel

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
