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
