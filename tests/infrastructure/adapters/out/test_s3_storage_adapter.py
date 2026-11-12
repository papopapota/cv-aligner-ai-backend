from collections.abc import Iterator

import boto3
import pytest
from botocore.config import Config
from moto import mock_aws
from mypy_boto3_s3.client import S3Client

from src.domain.errors import StorageError
from src.infrastructure.adapters.out.s3_storage_adapter import S3StorageAdapter
from src.infrastructure.config import S3Settings

BUCKET = "test-bucket"
KEY = "users/1/cv.pdf"


@pytest.fixture
def s3_client() -> Iterator[S3Client]:
    with mock_aws():
        yield boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="test",
            aws_secret_access_key="test",
            config=Config(signature_version="s3v4"),
        )


@pytest.fixture
def settings() -> S3Settings:
    return S3Settings(_env_file=None, bucket=BUCKET)


@pytest.fixture
def adapter(
    settings: S3Settings,
    s3_client: S3Client,
) -> S3StorageAdapter:
    return S3StorageAdapter(settings, client=s3_client)


def _create_bucket(s3_client: S3Client) -> None:
    s3_client.create_bucket(Bucket=BUCKET)


async def test_ensure_bucket_creates_a_missing_bucket(
    adapter: S3StorageAdapter,
    s3_client: S3Client,
) -> None:
    await adapter.ensure_bucket()

    s3_client.head_bucket(Bucket=BUCKET)


async def test_ensure_bucket_is_idempotent(
    adapter: S3StorageAdapter,
    s3_client: S3Client,
) -> None:
    await adapter.ensure_bucket()
    await adapter.ensure_bucket()

    s3_client.head_bucket(Bucket=BUCKET)


async def test_upload_and_download_round_trip(
    adapter: S3StorageAdapter,
    s3_client: S3Client,
) -> None:
    _create_bucket(s3_client)

    await adapter.upload(KEY, b"cv content", "application/pdf")

    assert await adapter.download(KEY) == b"cv content"
    head = s3_client.head_object(Bucket=BUCKET, Key=KEY)
    assert head["ContentType"] == "application/pdf"


async def test_download_missing_key_raises_storage_error(
    adapter: S3StorageAdapter,
    s3_client: S3Client,
) -> None:
    _create_bucket(s3_client)

    with pytest.raises(StorageError):
        await adapter.download("missing.pdf")


async def test_upload_to_missing_bucket_raises_storage_error(
    adapter: S3StorageAdapter,
) -> None:
    with pytest.raises(StorageError):
        await adapter.upload(KEY, b"cv content", "application/pdf")


async def test_delete_removes_the_object(
    adapter: S3StorageAdapter,
    s3_client: S3Client,
) -> None:
    _create_bucket(s3_client)
    await adapter.upload(KEY, b"cv content", "application/pdf")

    await adapter.delete(KEY)

    with pytest.raises(StorageError):
        await adapter.download(KEY)


async def test_delete_missing_key_is_idempotent(
    adapter: S3StorageAdapter,
    s3_client: S3Client,
) -> None:
    _create_bucket(s3_client)

    await adapter.delete("missing.pdf")


async def test_generate_presigned_url_points_to_the_object(
    adapter: S3StorageAdapter,
    s3_client: S3Client,
) -> None:
    _create_bucket(s3_client)
    await adapter.upload(KEY, b"cv content", "application/pdf")

    url = await adapter.generate_presigned_url(KEY, expires_in=120)

    assert BUCKET in url
    assert KEY in url
    assert "X-Amz-Expires=120" in url
