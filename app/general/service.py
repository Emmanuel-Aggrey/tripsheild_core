import io
import logging
import random
import tempfile
from datetime import datetime
from io import BytesIO
from typing import Optional
from typing import Tuple
from uuid import UUID
import pytz
import fitz
import magic
from app.core.models import BaseModel as Model
from app.general.s3_client import s3_service
from app.signals import post_delete
from app.signals import post_save
from app.signals import post_update
from fastapi import HTTPException
from fastapi import status
from moviepy.editor import VideoFileClip
from PIL import Image
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

    def create_thumbnail(
        self, s3_key: str, size: Tuple[int, int] = (128, 128)
    ) -> Optional[str]:
        try:
            if not s3_service.file_exists(s3_key):
                logging.error(f"File does not exist in S3: {s3_key}")
                return None

            image_data = s3_service.get_file_content(s3_key)
            if image_data is None:
                return None

            mime = magic.Magic(mime=True)
            mime_type = mime.from_buffer(image_data)

            if mime_type.startswith("image/"):
                return self.create_thumbnail_from_image(
                    image_data, s3_key, mime_type, size
                )
            elif mime_type.startswith("video/"):
                return self.create_thumbnail_from_video(s3_key, size)
            elif mime_type == "application/pdf":
                return self.create_pdf_thumbnail(s3_key, size)
            else:
                logging.error(f"Unsupported MIME type: {mime_type}")
                return self.generate_random_thumbnail(size)

        except Exception as e:
            logging.error(f"Error creating thumbnail: {str(e)}", exc_info=True)
            return None

    def create_thumbnail_from_image(
        self, image_data: bytes, s3_key: str, mime_type: str, size: Tuple[int, int]
    ):
        try:
            img = Image.open(BytesIO(image_data))

            if img.mode in ("RGBA", "LA") or (
                img.mode == "P" and "transparency" in img.info
            ):
                img = img.convert("RGB")
            img.thumbnail(size, Image.Resampling.LANCZOS)

            buffer = BytesIO()
            if mime_type == "image/jpeg":
                img.save(buffer, format="JPEG", quality=85, optimize=True)
            elif mime_type == "image/png":
                img.save(buffer, format="PNG", quality=85, optimize=True)
            elif mime_type == "image/gif":
                img.save(buffer, format="GIF", optimize=True)
            else:
                logging.error(f"Unsupported image MIME type: {mime_type}")
                return None

            buffer.seek(0)

            thumbnail_filename = "{}.jpg".format(
                s3_key.split("/")[-1].rsplit(".", 1)[0]
            )
            thumbnail_s3_path = f"thumbnails/{thumbnail_filename}"

            success = s3_service.upload_fileobj(
                buffer, thumbnail_s3_path, content_type="image/jpeg"
            )
            if not success:
                logging.error("Failed to upload thumbnail to S3.")
                return None

            return thumbnail_s3_path

        except Exception as e:
            message = f"Error creating image thumbnail: {str(e)}"
            logging.error(message, exc_info=True)

            return None

    def create_thumbnail_from_video(self, s3_key: str, size: Tuple[int, int]):
        try:
            video_data = s3_service.get_file_content(s3_key)
            if video_data is None:
                return None

            with tempfile.NamedTemporaryFile(delete=True) as temp_video_file:
                temp_video_file.write(video_data)
                temp_video_file.flush()

                with VideoFileClip(temp_video_file.name) as clip:
                    frame_time = clip.duration * 0.2
                    frame = clip.get_frame(frame_time)

                    img = Image.fromarray(frame)
                    img.thumbnail(size, Image.Resampling.LANCZOS)

                    buffer = BytesIO()
                    img.save(buffer, format="JPEG", quality=85, optimize=True)
                    buffer.seek(0)

                    thumbnail_filename = "{}.jpg".format(
                        s3_key.split("/")[-1].rsplit(".", 1)[0]
                    )
                    thumbnail_s3_path = f"thumbnails/{thumbnail_filename}"

                    success = s3_service.upload_fileobj(
                        buffer, thumbnail_s3_path, content_type="image/jpeg"
                    )
                    if not success:
                        logging.error(
                            "Failed to upload video thumbnail to S3.")
                        return None

                    return thumbnail_s3_path

        except Exception as e:
            message = f"Error creating video thumbnail: {str(e)}"
            logging.error(message, exc_info=True)

            return None

    def create_pdf_thumbnail(self, s3_key: str, size):
        file_content = s3_service.get_file_content(s3_key)
        if file_content is None:
            return

        try:
            pdf_file = fitz.open(stream=file_content, filetype="pdf")
            first_page = pdf_file.load_page(0)
            pix = first_page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img.thumbnail((300, 300))

            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            thumbnail_filename = "{}.jpg".format(
                s3_key.split("/")[-1].rsplit(".", 1)[0]
            )
            thumbnail_s3_path = f"thumbnails/{thumbnail_filename}"

            success = s3_service.upload_fileobj(
                buffer, thumbnail_s3_path, content_type="image/png"
            )
            if not success:
                logging.error("Failed to upload PDF thumbnail to S3.")
                return None

            return thumbnail_s3_path

        except Exception as e:
            message = f"Error creating PDF thumbnail: {str(e)}"
            logging.error(message, exc_info=True)

            return None

    def generate_random_thumbnail(self, size: Tuple[int, int]) -> str:
        img = Image.new("RGB", size, color=self.random_color())

        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85, optimize=True)
        buffer.seek(0)

        thumbnail_filename = f"{random.randint(1000, 9999)}.jpg"
        thumbnail_s3_path = f"thumbnails/{thumbnail_filename}"

        success = s3_service.upload_fileobj(
            buffer, thumbnail_s3_path, content_type="image/jpeg"
        )
        if not success:
            logging.error("Failed to upload random thumbnail to S3.")
            return None

        return thumbnail_s3_path

    def random_color(self) -> Tuple[int, int, int]:
        return random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
