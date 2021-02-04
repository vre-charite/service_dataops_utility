from pydantic import BaseModel, Field
from models.base_models import APIResponse

class ArchiveListGetResponse(APIResponse):
    result: dict = Field({}, example={   
              'container_id': 1129,
              'id': 1211,
              'labels': ['VirtualFolder'],
              'name': 'limittestfdsad',
              'time_created': '2020-12-09T15:08:29',
              'time_lastmodified': '2020-12-09T15:08:29'
          }
      )

