from fastapi import APIRouter
from api.api_virtual_folder import virtual_folders
from api.api_filedata_meta import filedata_meta

api_router = APIRouter()
api_router.include_router(virtual_folders.router, prefix="/vfolders", tags=["vfolder"])
api_router.include_router(virtual_folders.router, prefix="/vfolders", tags=["vfolder"])
api_router.include_router(filedata_meta.router, prefix="/filedata", tags=["filedata"])