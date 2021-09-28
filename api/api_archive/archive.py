from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv
from fastapi_sqlalchemy import db

from config import ConfigClass
from models.base_models import APIResponse, EAPIResponseCode
from models.api_archive_sql import ArchivePreviewModel
from models.api_archive import ArchiveGETResponse, ArchiveGETRequest, ArchivePOSTResponse, \
        ArchivePOSTRequest, ArchiveDELETERequest
from services.service_logger.logger_factory_service import SrvLoggerFactory

import requests
import os
import json
from zipfile import ZipFile

router = APIRouter()


@cbv(router)
class ArchiveList:
    _logger = SrvLoggerFactory('api_archive').get_logger()

    @router.get('/archive', response_model=ArchiveGETResponse, summary="Get a zip preview given geid")
    def get(self, data: dict = Depends(ArchiveGETRequest)):
        """ Get a Zip preview """
        file_geid = data.file_geid

        self._logger.info('Get zip preview for: ' + str(file_geid))
        api_response = ArchiveGETResponse()
        archive_model = db.session.query(ArchivePreviewModel).filter(
            ArchivePreviewModel.file_geid==file_geid, 
        ).first()

        if not archive_model:
            self._logger.info(f'Preview not found for file_geid: {file_geid}')
            api_response.code = EAPIResponseCode.not_found
            api_response.result = "Archive preview not found"
            return api_response.json_response()
        api_response.result = json.loads(archive_model.archive_preview)
        return api_response.json_response()

    @router.post('/archive', response_model=ArchivePOSTResponse, summary="Create a zip preview")
    def post(self, data: ArchivePOSTRequest):
        """ Create a ZIP preview given a file_geid and preview as a dict """
        file_geid = data.file_geid
        archive_preview = json.dumps(data.archive_preview)
        self._logger.info('POST zip preview for: ' + file_geid)
        api_response = ArchivePOSTResponse()
        try:
            query_result = db.session.query(ArchivePreviewModel).filter(
                ArchivePreviewModel.file_geid==file_geid, 
            ).first()
            if query_result:
                self._logger.info(f'Duplicate entry for file_geid: {file_geid}')
                api_response.code = EAPIResponseCode.conflict
                api_response.result = "Duplicate entry for preview"
                return api_response.json_response()

            archive_model = ArchivePreviewModel(
                file_geid=file_geid, 
                archive_preview=archive_preview
            )
            db.session.add(archive_model)
            db.session.commit()
        except Exception as e:
            self._logger.error("Psql error: " + str(e))
            api_response.error_msg = "Psql error: " + str(e)
            api_response.code = EAPIResponseCode.internal_error
            return api_response.json_response()
        api_response.result = "success"
        return api_response.json_response()

    @router.delete('/archive', summary="Delete a zip preview, only used for unit tests")
    def delete(self, data: ArchiveDELETERequest):
        """ Delete preview given a file_geid """
        file_geid = data.file_geid
        self._logger.info('DELETE zip preview for: ' + str(file_geid))
        api_response = APIResponse()
        try:
            archive_model = db.session.query(ArchivePreviewModel).filter(
                ArchivePreviewModel.file_geid==file_geid, 
            ).delete()
            db.session.commit()
        except Exception as e:
            self._logger.error("Psql error: " + str(e))
            api_response.error_msg = "Psql error: " + str(e)
            api_response.code = EAPIResponseCode.internal_error
            return api_response.json_response()
        api_response.result = "success"
        return api_response.json_response()
