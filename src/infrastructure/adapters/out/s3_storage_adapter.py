from __future__ import annotations

import asyncio

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from mypy_boto3_s3.client import S3Client

from src.application.ports.out.file_storage_port import FileStoragePort
from src.domain.errors import StorageError
from src.infrastructure.config import S3Settings

_MISSING_BUCKET_CODES = {"404", "NoSuchBucket", "NotFound"}


class S3StorageAdapter(FileStoragePort):
    """File storage backed by S3 (or an S3-compatible service such as LocalStack)."""

    def __init__(self, settings: S3Settings, client: S3Client | None = None) -> None:
        self._settings = settings
        self._client: S3Client = client or boto3.client(
            "s3",
            endpoint_url=settings.endpoint_url or None,
            region_name=settings.region,
            aws_access_key_id=settings.access_key_id,
            aws_secret_access_key=settings.secret_access_key,
            use_ssl=settings.use_ssl,
        )

    async def ensure_bucket(self) -> None:
        await asyncio.to_thread(self._ensure_bucket_sync)

    async def upload(self, key: str, content: bytes, content_type: str) -> None:
        await asyncio.to_thread(self._upload_sync, key, content, content_type)

    async def download(self, key: str) -> bytes:
        return await asyncio.to_thread(self._download_sync, key)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._delete_sync, key)

    async def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        return await asyncio.to_thread(
            self._generate_presigned_url_sync, key, expires_in
        )

    def _ensure_bucket_sync(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._settings.bucket)
            return
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code not in _MISSING_BUCKET_CODES:
                raise StorageError(
                    f"Could not verify the S3 bucket '{self._settings.bucket}': {exc}"
                ) from exc
        except BotoCoreError as exc:
            raise StorageError(
                f"Could not verify the S3 bucket '{self._settings.bucket}': {exc}"
            ) from exc

        try:
            self._client.create_bucket(Bucket=self._settings.bucket)
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(
                f"Could not create the S3 bucket '{self._settings.bucket}': {exc}"
            ) from exc

    def _upload_sync(self, key: str, content: bytes, content_type: str) -> None:
        try:
            self._client.put_object(
                Bucket=self._settings.bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(f"Could not upload '{key}' to S3: {exc}") from exc

    def _download_sync(self, key: str) -> bytes:
        try:
            response = self._client.get_object(
                Bucket=self._settings.bucket,
                Key=key,
            )
            body = response["Body"]
            return body.read()
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(f"Could not download '{key}' from S3: {exc}") from exc

    def _delete_sync(self, key: str) -> None:
        try:
            self._client.delete_object(
                Bucket=self._settings.bucket,
                Key=key,
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(f"Could not delete '{key}' from S3: {exc}") from exc

    def _generate_presigned_url_sync(self, key: str, expires_in: int) -> str:
        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._settings.bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(
                f"Could not generate a URL for '{key}': {exc}"
            ) from exc
