from typing import Any, Dict, Optional
from uuid import UUID
from datetime import date, datetime
from app.core.schema import BaseSchema
from pydantic import model_validator


class StorageStartRequest(BaseSchema):

    file_type: str
    filename: Optional[str] = None
    mime_type: Optional[str] = None


class StorageStartResponse(BaseSchema):
    id: UUID
    url: str
    fields: Optional[Dict[str, Any]] = None


class StorageFinishRequest(BaseSchema):
    pass


class StorageUpdate(BaseSchema):
    url: Optional[str] = None
    filename: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    s3_key: Optional[str] = None
    thumbnail: Optional[str] = None
    upload_finished_at: Optional[date] = None


class StorageResponse(BaseSchema):
    id: UUID
    url: str
    created_by: Optional[UUID] = None
    filename: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    s3_key: Optional[str] = None
    thumbnail: Optional[str] = None
    upload_finished_at: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def refresh_url(self):
        from app.core.dependency_injection import service_locator

        if self.s3_key:
            self.url = service_locator.s3_service.generate_presigned_get(
                self.s3_key)
        return self
