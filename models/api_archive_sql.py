# Copyright 2022 Indoc Research
# 
# Licensed under the EUPL, Version 1.2 or – as soon they
# will be approved by the European Commission - subsequent
# versions of the EUPL (the "Licence");
# You may not use this work except in compliance with the
# Licence.
# You may obtain a copy of the Licence at:
# 
# https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12
# 
# Unless required by applicable law or agreed to in
# writing, software distributed under the Licence is
# distributed on an "AS IS" basis,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied.
# See the Licence for the specific language governing
# permissions and limitations under the Licence.
# 

from fastapi_sqlalchemy import db
from config import ConfigClass
from sqlalchemy import Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()

class ArchivePreviewModel(Base):
    __tablename__ = "archive_preview"
    __table_args__ = {"schema": ConfigClass.RDS_SCHEMA_DEFAULT}
    id = Column(Integer, unique=True, primary_key=True)
    file_geid = Column(String())
    archive_preview = Column(String())

    def __init__(self, file_geid, archive_preview):
        self.file_geid = file_geid
        self.archive_preview = archive_preview

    def to_dict(self):
        result = {}
        for field in ["id", "file_geid", "archive_preview"]:
            result[field] = str(getattr(self, field))
        return result
