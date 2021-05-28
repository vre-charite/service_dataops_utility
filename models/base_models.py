from pydantic import BaseModel, validator, Field, root_validator
from fastapi.responses import JSONResponse
from enum import Enum


class EAPIResponseCode(Enum):
    success = 200
    internal_error = 500
    bad_request = 400
    not_found = 404
    forbidden = 403
    unauthorized = 401
    conflict = 409
    accepted = 202


class APIResponse(BaseModel):
  code: EAPIResponseCode = EAPIResponseCode.success
  error_msg: str = ""
  page: int = 0
  total: int = 1
  num_of_pages: int = 1
  result = []

  def json_response(self):
      data = self.dict()
      data["code"] = self.code.value
      return JSONResponse(status_code=self.code.value, content=data)


class PaginationRequest(BaseModel):
    page: int = 0
    page_size: int = 25 
    order_type: str = "asc"
    order_by: str = "createTime"
