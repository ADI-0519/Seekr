import io
import os

import pytest
from app.core.config import get_settings
from app.core.firebase_auth import require_firebase_user
from app.db.session import Base, get_db
from app.main import app
from app.services.storage import StorageService
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DB = "sqlite+aiosqlite:///:memory:"


# Resolve ednpoint URL
def resolve_endpoint_url() -> str | None:
    endpoint = os.getenv("STORAGE_ENDPOINT_URL")
    if not endpoint:
        return None
    if endpoint.startswith("http://minio:"):
        return endpoint.replace("http://minio:", "http://localhost:", 1)
    if endpoint.startswith("https://minio:"):
        return endpoint.replace("https://minio:", "https://localhost:", 1)
    return endpoint


# Fixtures for database and test client
@pytest.fixture
async def db():
    engine = create_async_engine(TEST_DB)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess
    await engine.dispose()


# Test client fixture with dependency override
@pytest.fixture
async def client(db, monkeypatch):
    def override():
        yield db

    app.dependency_overrides[get_db] = override
    monkeypatch.setattr(
        "app.api.videos.process_video.apply_async",
        lambda *_, **__: type("Result", (), {"id": "test-task-id"})(),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def auth_user():
    async def override_auth():
        return {"uid": "test-user-1", "email": "test@example.com"}

    app.dependency_overrides[require_firebase_user] = override_auth
    yield
    app.dependency_overrides.pop(require_firebase_user, None)


# Integration test for video upload endpoint
@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_creates_row_and_storage_path(client, monkeypatch):
    endpoint_url = resolve_endpoint_url()
    if not endpoint_url:
        pytest.skip("STORAGE_ENDPOINT_URL not set")

    monkeypatch.setenv("STORAGE_ENDPOINT_URL", endpoint_url)
    get_settings.cache_clear()

    data = {"title": "Integration Upload"}
    files = {"file": ("test.mp4", b"\x00\x00\x00\x18ftypisom" + b"\x00" * 64, "video/mp4")}

    resp = await client.post("/api/videos/upload", data=data, files=files)
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["id"] is not None
    assert payload["storage_path"] is not None

    storage = StorageService()
    output = io.BytesIO()
    storage.download_to_fileobj(payload["storage_path"], output)
    assert output.getvalue() == b"\x00\x00\x00\x18ftypisom" + b"\x00" * 64
