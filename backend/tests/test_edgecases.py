from unittest.mock import patch

import pytest
from app.core.firebase_auth import require_firebase_user
from app.db.session import Base, get_db
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession)

    async def override():
        async with factory() as s:
            yield s

    app.dependency_overrides[get_db] = override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture(autouse=True)
def auth_user():
    async def override_auth():
        return {"uid": "test-user-1", "email": "test@example.com"}

    app.dependency_overrides[require_firebase_user] = override_auth
    yield
    app.dependency_overrides.pop(require_firebase_user, None)


# malformed json


@pytest.mark.asyncio
async def test_bad_json(client):
    r = await client.post(
        "/api/videos/1/query", content="not json", headers={"Content-Type": "application/json"}
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_wrong_content_type(client):
    r = await client.post(
        "/api/videos/1/query", content='{"query": "test"}', headers={"Content-Type": "text/plain"}
    )
    assert r.status_code == 422


# missing required fields


@pytest.mark.asyncio
async def test_upload_no_title(client):
    r = await client.post("/api/videos/upload", data={})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_query_no_query_field(client):
    r = await client.post("/api/videos/1/query", json={})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_extra_fields_ignored(client):
    r = await client.post(
        "/api/videos/1/query", json={"query": "test", "foo": "bar", "random": 123}
    )
    # 404 bc video doesnt exist, but not 422
    assert r.status_code == 404


# empty body


@pytest.mark.asyncio
async def test_query_empty_body(client):
    r = await client.post("/api/videos/1/query")
    assert r.status_code == 422


# large payloads


@pytest.mark.asyncio
async def test_huge_title(client):
    with patch("app.api.videos.process_video.apply_async"):
        r = await client.post(
            "/api/videos/upload",
            data={"title": "a" * 10000, "youtube_url": "https://youtube.com/watch?v=abc"},
        )
    assert r.status_code in [200, 400, 422]


@pytest.mark.asyncio
async def test_huge_query(client):
    r = await client.post("/api/videos/1/query", json={"query": "word " * 5000})
    assert r.status_code in [404, 400, 422]
