import io
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from app.services.storage import StorageService
from botocore.exceptions import ClientError


def build_settings(**overrides):
    base = {
        "storage_bucket": "seekr-test",
        "storage_access_key_id": "key",
        "storage_secret_access_key": "secret",
        "storage_region": "eu-west-2",
        "storage_endpoint_url": "http://minio:9000",
        "storage_proxy_url": "",
        "storage_public_endpoint_url": "",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_init_requires_storage_credentials():
    with patch(
        "app.services.storage.get_settings",
        return_value=build_settings(storage_access_key_id="", storage_secret_access_key=""),
    ):
        with pytest.raises(ValueError, match="Storage credentials are required"):
            StorageService()


def test_init_requires_storage_bucket():
    with patch(
        "app.services.storage.get_settings",
        return_value=build_settings(storage_bucket=""),
    ):
        with pytest.raises(ValueError, match="Storage bucket is required"):
            StorageService()


def test_ensure_bucket_exists_creates_when_missing():
    client = MagicMock()
    client.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadBucket"
    )

    with patch("app.services.storage.get_settings", return_value=build_settings()):
        storage = StorageService()
    storage._client = client

    storage.ensure_bucket_exists()

    client.create_bucket.assert_called_once_with(
        Bucket="seekr-test",
        CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
    )


def test_ensure_bucket_exists_creates_without_location_for_us_east_1():
    client = MagicMock()
    client.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "NoSuchBucket", "Message": "Not Found"}}, "HeadBucket"
    )

    with patch(
        "app.services.storage.get_settings",
        return_value=build_settings(storage_region="us-east-1"),
    ):
        storage = StorageService()
    storage._client = client

    storage.ensure_bucket_exists()

    client.create_bucket.assert_called_once_with(Bucket="seekr-test")


def test_ensure_bucket_exists_skips_create_when_already_present():
    client = MagicMock()

    with patch("app.services.storage.get_settings", return_value=build_settings()):
        storage = StorageService()
    storage._client = client

    storage.ensure_bucket_exists()

    client.head_bucket.assert_called_once_with(Bucket="seekr-test")
    client.create_bucket.assert_not_called()


def test_upload_fileobj_sanitizes_key_and_sets_content_type():
    client = MagicMock()
    blob = io.BytesIO(b"hello")

    with patch("app.services.storage.get_settings", return_value=build_settings()):
        storage = StorageService()
    storage._client = client

    out = storage.upload_fileobj(blob, "/unsafe/../slides\\\\a b?.jpg", content_type="image/jpeg")

    assert out == "unsafe/slides/a_b_.jpg"
    client.upload_fileobj.assert_called_once()
    _, kwargs = client.upload_fileobj.call_args
    assert kwargs["Bucket"] == "seekr-test"
    assert kwargs["Key"] == "unsafe/slides/a_b_.jpg"
    assert kwargs["ExtraArgs"] == {"ContentType": "image/jpeg"}


def test_delete_object_ignores_not_found_errors():
    client = MagicMock()
    client.delete_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "Missing"}}, "DeleteObject"
    )

    with patch("app.services.storage.get_settings", return_value=build_settings()):
        storage = StorageService()
    storage._client = client

    storage.delete_object("videos/1/missing.mp4")

    client.delete_object.assert_called_once()


def test_delete_object_raises_for_non_404_errors():
    client = MagicMock()
    client.delete_object.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Denied"}}, "DeleteObject"
    )

    with patch("app.services.storage.get_settings", return_value=build_settings()):
        storage = StorageService()
    storage._client = client

    with pytest.raises(ClientError):
        storage.delete_object("videos/1/protected.mp4")


def test_get_presigned_url_uses_proxy_when_configured():
    with patch(
        "app.services.storage.get_settings",
        return_value=build_settings(storage_proxy_url="https://api.example.com"),
    ):
        storage = StorageService()

    url = storage.get_presigned_url("/videos/3/test file.mp4")
    assert url == "https://api.example.com/api/media/videos/3/test_file.mp4"


def test_get_object_stream_forwards_range_header():
    client = MagicMock()
    client.get_object.return_value = {
        "Body": b"x",
        "ContentType": "video/mp4",
        "ContentLength": 100,
        "ContentRange": "bytes 0-99/100",
    }

    with patch("app.services.storage.get_settings", return_value=build_settings()):
        storage = StorageService()
    storage._client = client

    body, content_type, length, content_range = storage.get_object_stream(
        "videos/2/sample.mp4", range_header="bytes=0-99"
    )

    assert body == b"x"
    assert content_type == "video/mp4"
    assert length == 100
    assert content_range == "bytes 0-99/100"
    client.get_object.assert_called_once_with(
        Bucket="seekr-test",
        Key="videos/2/sample.mp4",
        Range="bytes=0-99",
    )
