from fastapi import APIRouter
from api.api_virtual_folder import virtual_folders, virtual_folder_file
from api.api_filedata_meta import filedata_meta
from api.api_file_operations import api_file_operations
from api.api_task_dispatch import task_dispatch
from api.api_file_operations import api_file_operations_validate

api_router = APIRouter()
api_router.include_router(virtual_folders.router, prefix="/collections", tags=["collections"])
api_router.include_router(virtual_folder_file.router, prefix="/collections", tags=["collections"])
api_router.include_router(filedata_meta.router, prefix="/filedata", tags=["filedata"])
api_router.include_router(task_dispatch.router, prefix="/tasks", tags=["task-management"])
api_router.include_router(api_file_operations.router, prefix="/files/actions", tags=["file-operations"])
api_router.include_router(api_file_operations_validate.router, prefix="/files/actions/validate", tags=["file-operations-validate"])
