from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi_utils.cbv import cbv
from sqlalchemy.orm import Session
from datetime import date
from app.core.dependency_injection import service_locator
from app.storage.models import Storage
from app.storage.schemas import StorageResponse, StorageUpdate
from app.storage.schemas import StorageStartRequest, StorageStartResponse, StorageFinishRequest
from app.dependencies import get_db
from app.authentication.utils import get_current_active_user
from app.accounts.models import User

router = APIRouter(dependencies=[Depends(get_current_active_user)])


@cbv(router)
class AttachmentsView:
    db: Session = Depends(get_db)
    current_user: User = Depends(get_current_active_user)

    @router.post("/start/", response_model=StorageStartResponse, status_code=201)
    def start_upload(self, payload: StorageStartRequest):
        import uuid
        s3_key = f"{uuid.uuid4()}/{payload.filename or 'file'}"

        presigned = service_locator.s3_service.generate_presigned_post(
            key=s3_key, content_type=payload.file_type
        )
        upload_url = presigned["url"]
        fields = presigned["fields"]
        url = service_locator.s3_service.get_file_url(s3_key) or ""
        storage = service_locator.general_service.create_data(
            db=self.db,
            data={
                "created_by": self.current_user.id,
                "s3_key": s3_key,
                "url": url,
                "filename": payload.filename,
                "mime_type": payload.mime_type or payload.file_type,
            },
            model=Storage,
        )
        return StorageStartResponse(id=storage.id, url=upload_url, fields=fields)

    @router.post("/{id}/finish/", response_model=StorageResponse)
    def finish_upload(self, id: UUID, payload: StorageFinishRequest):
        storage: Storage = service_locator.general_service.get_data_by_id(
            db=self.db, key=id, model=Storage)

        data = {
            "upload_finished_at": date.today(),
            "file_size": service_locator.s3_service.get_file_size(storage.s3_key) or None,
        }
        return service_locator.general_service.update_data(
            db=self.db, key=id, data=data, model=Storage
        )

    @router.get("/{id}/", response_model=StorageResponse)
    def get_attachment(self, id: UUID):
        storage = service_locator.general_service.get_data_by_id(
            db=self.db, key=id, model=Storage)
        if not storage:
            raise HTTPException(status_code=404, detail="Attachment not found")
        return storage

    @router.put("/{id}/", response_model=StorageResponse)
    def update_attachment(self, id: UUID, payload: StorageUpdate):
        storage = service_locator.general_service.update_data(
            db=self.db, key=id, data=payload.model_dump(exclude_unset=True), model=Storage
        )
        if not storage:
            raise HTTPException(status_code=404, detail="Attachment not found")
        return storage

    @router.delete("/{id}/", status_code=204)
    def delete_attachment(self, id: UUID):
        storage: Storage = service_locator.general_service.get_data_by_id(
            db=self.db, key=id, model=Storage)
        if not storage:
            raise HTTPException(status_code=404, detail="Attachment not found")
        if storage.s3_key:
            service_locator.s3_service.delete_object(storage.s3_key)
        service_locator.general_service.delete_data(
            db=self.db, key=id, model=Storage)
