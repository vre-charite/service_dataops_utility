from fastapi import APIRouter
from api.api_virtual_folder import virtual_folders, virtual_folder_file
from api.api_filedata_meta import filedata_meta
from api.api_file_operations import api_file_operations
from api.api_task_dispatch import task_dispatch
from api.api_file_operations import api_file_operations_validate
from api.api_file_operations import api_message_hub
from api.api_tags import tags_api, batch_tags_operation_v2
from api.api_resource_lock import api_r_lock, api_file_lock
from api.api_archive import archive

api_router = APIRouter()
api_router.include_router(virtual_folders.router, prefix="/collections", tags=["collections"])
api_router.include_router(virtual_folder_file.router, prefix="/collections", tags=["collections"])
api_router.include_router(filedata_meta.router, prefix="/filedata", tags=["filedata"])
api_router.include_router(task_dispatch.router, prefix="/tasks", tags=["task-management"])
api_router.include_router(api_file_operations.router, prefix="/files/actions", tags=["file-operations"])
api_router.include_router(api_file_operations_validate.router, prefix="/files/actions/validate", tags=["file-operations-validate"])
api_router.include_router(api_message_hub.router, prefix="/files/actions/message", tags=["file-actions-message-hub"])

api_router.include_router(api_r_lock.router, prefix="/resource/lock", tags=["resource-lock"])

api_router.include_router(archive.router, prefix="", tags=["archive"])

api_router_v2 = APIRouter()
api_router_v2.include_router(batch_tags_operation_v2.router, prefix="/entity", tags=["Batch operation to update tags"])
api_router_v2.include_router(tags_api.router, prefix="/{entity_type}", tags=["tags api"])
api_router_v2.include_router(api_file_lock.router, prefix="/resource/lock", tags=["resource-lock"])
