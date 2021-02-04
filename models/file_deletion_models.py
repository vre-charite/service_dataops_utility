
from pydantic import BaseModel, Field
from models.base_models import APIResponse

### FileDeletion ###
class FiledataDeletionPOST(BaseModel):
    to_delete: list
    operator: str
    session_id: str
    job_id: str
    project_code: str

class FiledataDeletionPOSTResponse(APIResponse):
    result: dict = Field({}, example={
        'message': 'Succeed',
    }
  )
