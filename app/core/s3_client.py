
import logging
import uuid
from typing import Optional

import boto3
from botocore.client import Config
from app import settings
from botocore.exceptions import ClientError
import urllib.parse


logger = logging.getLogger(__name__)


class S3Service:
    def __init__(self, base_path: str = "", bucket_name=settings.BUCKET_NAME):

        self._client = None
        self.bucket_name = settings.BUCKET_NAME
        self.base_path = base_path.rstrip('/') + '/' if base_path else ""

    def init(self) -> "S3Service":
        if self._client is not None:
            return self
        if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
            raise RuntimeError(
                "AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY are not set in environment."
            )
        if not settings.BUCKET_NAME:
            raise RuntimeError(
                "BUCKET_NAME (or AWS_STORAGE_BUCKET_NAME) is not set.")

        self._client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
            config=Config(signature_version="s3v4"),
        )
        logger.info(
            "S3 client ready (bucket=%s, region=%s)",
            settings.BUCKET_NAME,
            settings.AWS_S3_REGION_NAME,
        )
        return self

    @property
    def client(self):
        if self._client is None:
            self.init()
        return self._client

    @property
    def bucket(self) -> str:
        return settings.BUCKET_NAME

    @staticmethod
    def build_key(category: str, user_id: str, filename: str) -> str:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
        APPLICATION_NAME = settings.APP_NAME
        return f"{APPLICATION_NAME}/{category}/{user_id}/{uuid.uuid4().hex}.{ext}"

    def generate_presigned_post(
        self,
        key: str,
        content_type: str,
        max_size_bytes: int = 100 * 1024 * 1024,
        expires_in: int = 900,
    ) -> dict:
        conditions = [
            {"Content-Type": content_type},
            ["content-length-range", 0, max_size_bytes],
        ]
        fields = {"Content-Type": content_type}

        return self.client.generate_presigned_post(
            Bucket=self.bucket,
            Key=key,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=expires_in,
        )

    def generate_presigned_get(self, key: str, expires_in: int = 3600, download: bool = False) -> str | None:
        if not self.object_exists(key):
            return None
        params = {"Bucket": self.bucket, "Key": key}
        if download:
            params["ResponseContentDisposition"] = "attachment"
        return self.client.generate_presigned_url("get_object", Params=params, ExpiresIn=expires_in)

    def put_object(self, key: str, data: bytes, content_type: str) -> None:

        self.client.put_object(
            Bucket=self.bucket, Key=key, Body=data, ContentType=content_type,
        )

    def get_object(self, key: str) -> tuple[bytes, str]:
        if not self.object_exists(key):
            raise FileExistsError(f"Object with key '{key}' does not exist.")

        resp = self.client.get_object(Bucket=self.bucket, Key=key)
        return resp["Body"].read(), resp.get("ContentType", "application/octet-stream")

    def object_exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def delete_object(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def head_object(self, key: str) -> dict | None:
        try:
            return self.client.head_object(Bucket=self.bucket, Key=key)
        except Exception:
            return None

    def get_file_size(self, key: str) -> int:
        if not self.file_exists(key):
            return 0

        try:
            response = self.client.head_object(
                Bucket=self.bucket_name, Key=self._path(key))
            return response["ContentLength"]
        except self.client.exceptions.ClientError:
            raise

    def file_exists(self, key: str) -> bool:
        try:

            self.client.head_object(
                Bucket=self.bucket_name, Key=self._path(key))
            return True
        except self.client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    def get_file_path(self, object_name: str):
        key = self._path(object_name)
        if self.file_exists(object_name):
            return f"https://{self.bucket_name}.s3.amazonaws.com/{key}"
        return None

    def get_file_url(self, object_name: str) -> Optional[str]:
        try:
            encoded_name = urllib.parse.quote(self._path(object_name))
            return f"https://{self.bucket_name}.s3.amazonaws.com/{encoded_name}"

        except Exception as e:
            logging.error(f"Failed to generate URL for {object_name}: {e}")
            return None

    def get_file_content(self, object_name: str) -> Optional[bytes]:
        key = self._path(object_name)
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=key)
            return response["Body"].read()
        except ClientError as e:
            logging.error("Failed to fetch file %s: %s", key,
                          e.response["Error"]["Message"])
            return None

    def _path(self, key: str) -> str:
        """Add base path if provided"""
        if not self.base_path or key.startswith(self.base_path):
            return key
        return f"{self.base_path}{key}"
