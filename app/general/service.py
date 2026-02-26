
from datetime import datetime

from uuid import UUID
import pytz
from app.core.models import BaseModel as Model
from app.signals import post_delete
from app.signals import post_save
from app.signals import post_update
from fastapi import HTTPException
from fastapi import status
from pydantic import BaseModel
from pydantic import UUID4
from sqlalchemy.orm import Session
from typing import Any


def serialize_data(data: dict) -> dict:
    serialized = {}
    for key, value in data.items():
        if isinstance(value, UUID):
            serialized[key] = str(value)
        elif isinstance(value, datetime):
            serialized[key] = value.isoformat()
        else:
            serialized[key] = value
    return serialized


class GeneralService:
    def create_data(self, db: Session, model: Any, data: dict = None) -> Model:

        instance = model(**data) if data else model()

        db.add(instance)

        db.commit()
        db.refresh(instance)

        post_save.send(sender=model, instance=instance,
                       created=True, kwargs=data)

        return instance

    def list_data(self, db: Session, model: BaseModel):
        return db.query(model).all()

    def get_data_by_id(self, db: Session, key: UUID4, model: BaseModel):
        data = db.query(model).filter(model.id == key).one_or_none()

        self.raise_not_found(data)
        return data

    def delete_data(self, db: Session, key: UUID4, model: BaseModel, **kwargs: dict):
        data = db.query(model).filter(model.id == key).first()

        self.raise_not_found(data)
        db.delete(data)
        db.commit()

        post_delete.send(sender=model, instance=model,
                         created=False, kwargs=kwargs)

        return

    def update_data(
        self, db: Session, key: UUID4, data: dict, model: BaseModel
    ) -> Model:
        project = db.query(model).filter(model.id == key).first()
        self.raise_not_found(project)

        for key, value in data.items():
            if hasattr(project, key):
                setattr(project, key, value)

        db.commit()
        db.refresh(project)

        post_update.send(
            sender=model, instance=model, created=False, kwargs=serialize_data(data)
        )

        return project

    def filter_data(
        self,
        db: Session,
        filter_values: dict,
        model: BaseModel,
        single_record: bool = False,
    ):
        query = db.query(model)

        for key, value in filter_values.items():
            if hasattr(model, key):
                query = query.filter(getattr(model, key) == value)

        return query.one_or_none() if single_record else query.all()

    def validate_timezone(self, timezone: str) -> bool:
        try:
            pytz.timezone(timezone)
            return True
        except pytz.UnknownTimeZoneError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": f"Invalid timezone provided {timezone}"},
            )

    def convert_datetime_to_timezone(self, datetime_value: datetime, timezone: str = "UTC") -> datetime:

        if datetime_value.tzinfo is None:
            datetime_value = pytz.utc.localize(datetime_value)

        target_timezone = pytz.timezone(timezone)
        return datetime_value.astimezone(target_timezone)

    def raise_not_found(self, model: BaseModel, message="Not Found"):
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{status.HTTP_404_NOT_FOUND} {message}",
            )
        return object
