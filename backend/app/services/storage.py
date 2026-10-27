import re
import uuid
from pathlib import Path

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core.config import get_settings


# Service class to manage interactions with S3-compatible object storage
class StorageService:
    def __init__(self):
        self._client = None
        self._settings = get_settings()
        self._bucket = self._settings.storage_bucket

        if not self._settings.storage_access_key_id or not self._settings.storage_secret_access_key:
            raise ValueError("Storage credentials are required")
        if not self._bucket:
            raise ValueError("Storage bucket is required")

    @property
    def bucket(self) -> str:
        return self._bucket

    # Initialize and cache the boto3 S3 client with standard timeout and retry configurations
    def get_client(self):
        if self._client is None:
            cfg = BotoConfig(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=10,
                read_timeout=30,
            )
            kwargs = {
                "aws_access_key_id": self._settings.storage_access_key_id,
                "aws_secret_access_key": self._settings.storage_secret_access_key,
                "region_name": self._settings.storage_region,
                "config": cfg,
            }
            if self._settings.storage_endpoint_url:
                kwargs["endpoint_url"] = self._settings.storage_endpoint_url
            self._client = boto3.client("s3", **kwargs)

        return self._client

    # Verify the target storage bucket exists and create it if it does not
    def ensure_bucket_exists(self) -> None:
        client = self.get_client()

        try:
            client.head_bucket(Bucket=self._bucket)
            return
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("404", "NoSuchBucket", "NotFound"):
                params: dict = {"Bucket": self._bucket}
                if self._settings.storage_region and self._settings.storage_region != "us-east-1":
                    params["CreateBucketConfiguration"] = {
                        "LocationConstraint": self._settings.storage_region
                    }
                client.create_bucket(**params)
                return
            raise

    # Sanitize file paths to prevent directory traversal attacks and invalid characters
    def sanitize_key(self, key: str) -> str:
        key = key.lstrip("/").replace("\\", "/")
        key = re.sub(r"/+", "/", key)
        parts = []

        for part in key.split("/"):
            if not part or part in (".", ".."):
                continue
            part = re.sub(r"[^a-zA-Z0-9._-]", "_", part)
            parts.append(part)

        return "/".join(parts)

    # Generate a unique storage path for a video file
    def generate_object_key(self, video_id: int, filename: str | None) -> str:
        file_uuid = str(uuid.uuid4())

        if filename:
            ext = Path(filename).suffix.lower()
        else:
            ext = ".mp4"

        name = f"{file_uuid}{ext}"
        key = f"videos/{video_id}/{name}"
        return self.sanitize_key(key)

    # Generate a unique storage path for an extracted audio file
    def generate_audio_key(self, video_id: int) -> str:
        file_uuid = str(uuid.uuid4())
        key = f"audio/{video_id}/{file_uuid}.wav"
        return self.sanitize_key(key)

    # Generate a unique storage path for a video thumbnail image
    def generate_thumbnail_key(self, video_id: int) -> str:
        file_uuid = str(uuid.uuid4())
        key = f"thumbnails/{video_id}/{file_uuid}.jpg"
        return self.sanitize_key(key)

    # Generate a unique storage path for an extracted presentation slide
    def generate_slide_frame_key(self, video_id: int, index: int) -> str:
        file_uuid = str(uuid.uuid4())
        key = f"slides/{video_id}/{file_uuid}_{index}.jpg"
        return self.sanitize_key(key)

    # Stream a local file object directly into the cloud storage bucket
    def upload_fileobj(self, fileobj, key: str, content_type: str | None = None) -> str:
        client = self.get_client()
        safe_key = self.sanitize_key(key)
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        client.upload_fileobj(
            Fileobj=fileobj,
            Bucket=self._bucket,
            Key=safe_key,
            ExtraArgs=extra_args if extra_args else None,
        )
        return safe_key

    # Download a file from the bucket directly into a local file object
    def download_to_fileobj(self, key: str, fileobj) -> None:
        client = self.get_client()
        safe_key = self.sanitize_key(key)
        client.download_fileobj(self._bucket, safe_key, fileobj)

    # Remove a file from the bucket, silently ignoring 404 errors if the file is already gone
    def delete_object(self, key: str) -> None:
        client = self.get_client()
        safe_key = self.sanitize_key(key)
        try:
            client.delete_object(Bucket=self._bucket, Key=safe_key)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code not in ("404", "NoSuchKey", "NotFound"):
                raise

    # Generate a temporary, secure URL for frontend clients to access a private file
    def get_presigned_url(self, key: str, expires: int = 3600) -> str:
        safe_key = self.sanitize_key(key)
        proxy_url = (self._settings.storage_proxy_url or "").strip()

        if proxy_url:
            return f"{proxy_url}/api/media/{safe_key}"

        cfg = BotoConfig(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
            connect_timeout=10,
            read_timeout=30,
        )
        public_endpoint = (self._settings.storage_public_endpoint_url or "").strip()
        presign_endpoint = public_endpoint or (self._settings.storage_endpoint_url or "").strip()
        internal_client = (
            boto3.client(
                "s3",
                aws_access_key_id=self._settings.storage_access_key_id,
                aws_secret_access_key=self._settings.storage_secret_access_key,
                region_name=self._settings.storage_region,
                endpoint_url=presign_endpoint,
                config=cfg,
            )
            if presign_endpoint
            else self.get_client()
        )

        url = internal_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": safe_key},
            ExpiresIn=expires,
        )

        return str(url)

    # Fetch a file as a continuous stream, supporting HTTP byte-range requests for video playback
    def get_object_stream(self, key: str, range_header: str | None = None):
        client = self.get_client()
        safe_key = self.sanitize_key(key)
        kwargs = {"Bucket": self._bucket, "Key": safe_key}
        if range_header:
            kwargs["Range"] = range_header

        response = client.get_object(**kwargs)
        return (
            response["Body"],
            response.get("ContentType", "application/octet-stream"),
            response.get("ContentLength"),
            response.get("ContentRange"),
        )
