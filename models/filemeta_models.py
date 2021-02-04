from pydantic import BaseModel, Field
from models.base_models import APIResponse

### FiledataMeta ###
class FiledataMetaPOST(BaseModel):
    uploader: str 
    file_name: str 
    path: str 
    file_size: int 
    description: str 
    namespace: str 
    data_type: str
    labels: list 
    project_code: str 
    generate_id: str = ""
    process_pipeline: str = ""
    operator: str = ""
    parent_query: dict = {}


class FiledataMetaPOSTResponse(APIResponse):
    result: dict = Field({}, example={   
        'archived': False,
        'file_size': 1024,
        'full_path': '/data/vre-storage/generate/raw/BCD-1234_file_2.aacn',
        'generate_id': 'BCD-1234_2',
        'guid': '5321880a-1a41-4bc8-a5d5-9767323205792',
        'id': 478,
        'labels': ['VRECore', 'File', 'Processed'],
        'name': 'BCD-1234_file_2.aacn',
        'namespace': 'core',
        'path': '/data/vre-storage/generate/raw',
        'process_pipeline': 'greg_testing',
        'time_created': '2021-01-06T18:02:55',
        'time_lastmodified': '2021-01-06T18:02:55',
        'type': 'processed',
        'uploader': 'admin',
        'operator': 'admin'
      }
  )
