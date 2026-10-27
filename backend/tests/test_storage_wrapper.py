import io
import os
import uuid

import pytest
from app.core.config import get_settings
from app.services.storage import StorageService


# Helper function
def resolve_endpoint_url() -> str | None:
    endpoint = os.getenv("STORAGE_ENDPOINT_URL")
    if not endpoint:
        return None
    if endpoint.startswith("http://minio:"):
        return endpoint.replace("http://minio:", "http://localhost:", 1)
    if endpoint.startswith("https://minio:"):
        return endpoint.replace("https://minio:", "https://localhost:", 1)
    return endpoint


# Test Upload and Download
@pytest.mark.integration
def test_storage_upload_download(monkeypatch):
    endpoint_url = resolve_endpoint_url()
    if not endpoint_url:
        pytest.skip("STORAGE_ENDPOINT_URL not set")

    required = [
        "STORAGE_BUCKET",
        "STORAGE_ACCESS_KEY_ID",
        "STORAGE_SECRET_ACCESS_KEY",
    ]
    if any(not os.getenv(name) for name in required):
        pytest.skip("Storage credentials not set")

    monkeypatch.setenv("STORAGE_ENDPOINT_URL", endpoint_url)
    get_settings.cache_clear()

    storage = StorageService()
    storage.ensure_bucket_exists()

    key = f"tests/{uuid.uuid4().hex}.txt"
    payload = b"hello storage"
    file_obj = io.BytesIO(payload)

    uploaded_key = storage.upload_fileobj(file_obj, key, content_type="text/plain")
    assert uploaded_key.endswith(".txt")

    output = io.BytesIO()
    storage.download_to_fileobj(uploaded_key, output)
    assert output.getvalue() == payload
