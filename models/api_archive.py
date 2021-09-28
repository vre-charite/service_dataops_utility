from pydantic import BaseModel, Field
from models.base_models import APIResponse, PaginationRequest

class ArchiveGETResponse(APIResponse):
    result: dict = Field({}, example={})

class ArchiveGETRequest(BaseModel):
    file_geid: str

class ArchivePOSTResponse(APIResponse):
    result: dict = Field({}, example={})

class ArchivePOSTRequest(BaseModel):
    file_geid: str
    archive_preview: dict

class ArchiveDELETERequest(BaseModel):
    file_geid: str
