from unittest.mock import MagicMock, patch

import pytest
from app.core.config import get_settings
from app.db.session import Base, get_db
from app.main import app
from app.models.video import Video
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DB = "sqlite+aiosqlite:///:memory:"

FAKE_UID = "test-uid-123"
FAKE_USER = {"uid": FAKE_UID, "email": "test@example.com"}


@pytest.fixture
async def db():
    engine = create_async_engine(TEST_DB)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession)
    async with factory() as sess:
        yield sess
    await engine.dispose()


@pytest.fixture
async def client_auth_enabled(db):
    """Client with Firebase auth enabled — tokens are verified against FAKE_USER."""

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    get_settings.cache_clear()

    with (
        patch.dict("os.environ", {"FIREBASE_AUTH_ENABLED": "true"}),
        patch("app.core.firebase_auth.get_firebase_app", return_value=object()),
        patch("app.core.firebase_auth.auth.verify_id_token", return_value=FAKE_USER),
    ):
        get_settings.cache_clear()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c

    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture
async def client_no_auth(db):
    """Client with Firebase auth disabled — all requests pass without a token."""

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    get_settings.cache_clear()

    with patch.dict("os.environ", {"FIREBASE_AUTH_ENABLED": "false"}):
        get_settings.cache_clear()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c

    app.dependency_overrides.clear()
    get_settings.cache_clear()


VALID_TOKEN_HEADER = {"Authorization": "Bearer valid-test-token"}


class TestUnauthenticated401:
    """Every protected endpoint must return 401 when no token is provided."""

    @pytest.mark.asyncio
    async def test_list_videos(self, client_auth_enabled):
        r = await client_auth_enabled.get("/api/videos/")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_get_video(self, client_auth_enabled):
        r = await client_auth_enabled.get("/api/videos/1")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_upload_video(self, client_auth_enabled):
        r = await client_auth_enabled.post("/api/videos/upload", data={"title": "Test"})
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_submit_youtube(self, client_auth_enabled):
        r = await client_auth_enabled.post(
            "/api/videos/youtube",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_video(self, client_auth_enabled):
        r = await client_auth_enabled.delete("/api/videos/1")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_get_status(self, client_auth_enabled):
        r = await client_auth_enabled.get("/api/videos/1/status")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_get_transcript(self, client_auth_enabled):
        r = await client_auth_enabled.get("/api/videos/1/transcript")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_get_slides(self, client_auth_enabled):
        r = await client_auth_enabled.get("/api/videos/1/slides")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_download_slides(self, client_auth_enabled):
        r = await client_auth_enabled.get("/api/videos/1/slides/download")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_query(self, client_auth_enabled):
        r = await client_auth_enabled.post("/api/videos/1/query", json={"query": "test"})
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_get_notes(self, client_auth_enabled):
        r = await client_auth_enabled.get("/api/videos/1/notes")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_qdrant_health(self, client_auth_enabled):
        r = await client_auth_enabled.get("/api/videos/qdrant/health")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_qdrant_seed(self, client_auth_enabled):
        r = await client_auth_enabled.post("/api/videos/qdrant/seed/1")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_get_chat_history(self, client_auth_enabled):
        r = await client_auth_enabled.get("/api/videos/1/chat")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_save_chat_history(self, client_auth_enabled):
        r = await client_auth_enabled.put("/api/videos/1/chat", json={"messages": []})
        assert r.status_code == 401


class TestAuthDisabled:
    """When firebase_auth_enabled=False, requests without a token must still work."""

    @pytest.mark.asyncio
    async def test_list_videos_passes_without_token(self, client_no_auth):
        r = await client_no_auth.get("/api/videos/")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_health_always_public(self, client_no_auth):
        r = await client_no_auth.get("/health")
        assert r.status_code == 200


class TestOwnership:
    """Videos created by one user must not be accessible by another."""

    @pytest.mark.asyncio
    async def test_user_cannot_access_another_users_video(self, db, client_auth_enabled):
        other_video = Video(title="Other User Video", status="complete", owner_uid="other-uid-999")
        db.add(other_video)
        await db.flush()
        video_id = other_video.id
        await db.commit()

        r = await client_auth_enabled.get(
            f"/api/videos/{video_id}",
            headers=VALID_TOKEN_HEADER,
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_user_can_access_own_video(self, db, client_auth_enabled):
        own_video = Video(title="My Video", status="complete", owner_uid=FAKE_UID)
        db.add(own_video)
        await db.flush()
        video_id = own_video.id
        await db.commit()

        r = await client_auth_enabled.get(
            f"/api/videos/{video_id}",
            headers=VALID_TOKEN_HEADER,
        )
        assert r.status_code == 200
        assert r.json()["id"] == video_id

    @pytest.mark.asyncio
    async def test_user_cannot_delete_another_users_video(self, db, client_auth_enabled):
        other_video = Video(title="Not Mine", status="complete", owner_uid="other-uid-999")
        db.add(other_video)
        await db.flush()
        video_id = other_video.id
        await db.commit()

        r = await client_auth_enabled.delete(
            f"/api/videos/{video_id}",
            headers=VALID_TOKEN_HEADER,
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_list_only_returns_own_videos(self, db, client_auth_enabled):
        db.add(Video(title="Mine", status="complete", owner_uid=FAKE_UID))
        db.add(Video(title="Not Mine", status="complete", owner_uid="other-uid-999"))
        await db.commit()

        r = await client_auth_enabled.get("/api/videos/", headers=VALID_TOKEN_HEADER)
        assert r.status_code == 200
        titles = [v["title"] for v in r.json()]
        assert "Mine" in titles
        assert "Not Mine" not in titles

    @pytest.mark.asyncio
    async def test_user_cannot_query_another_users_video(self, db, client_auth_enabled):
        other_video = Video(title="Not Mine", status="complete", owner_uid="other-uid-999")
        db.add(other_video)
        await db.flush()
        video_id = other_video.id
        await db.commit()

        r = await client_auth_enabled.post(
            f"/api/videos/{video_id}/query",
            json={"query": "test"},
            headers=VALID_TOKEN_HEADER,
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_query_works_with_auth(self, db, client_auth_enabled):
        own_video = Video(title="My Video", status="complete", owner_uid=FAKE_UID)
        db.add(own_video)
        await db.flush()
        video_id = own_video.id
        await db.commit()

        mock_result = MagicMock()
        mock_result.get.return_value = {"results": [], "answer": "test answer", "citations": []}

        with (
            patch("app.api.videos.run_query") as mock_run_query,
            patch("app.api.videos.get_redis", side_effect=Exception("no redis")),
        ):
            mock_run_query.delay.return_value = mock_result
            r = await client_auth_enabled.post(
                f"/api/videos/{video_id}/query",
                json={"query": "what is this lecture about?"},
                headers=VALID_TOKEN_HEADER,
            )

        assert r.status_code == 200
        assert r.json()["query"] == "what is this lecture about?"

    @pytest.mark.asyncio
    async def test_user_cannot_read_another_users_chat(self, db, client_auth_enabled):
        other_video = Video(title="Not Mine", status="complete", owner_uid="other-uid-999")
        db.add(other_video)
        await db.flush()
        video_id = other_video.id
        await db.commit()

        r = await client_auth_enabled.get(
            f"/api/videos/{video_id}/chat",
            headers=VALID_TOKEN_HEADER,
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_write_another_users_chat(self, db, client_auth_enabled):
        other_video = Video(title="Not Mine", status="complete", owner_uid="other-uid-999")
        db.add(other_video)
        await db.flush()
        video_id = other_video.id
        await db.commit()

        r = await client_auth_enabled.put(
            f"/api/videos/{video_id}/chat",
            json={"messages": [{"role": "user", "text": "hello"}]},
            headers=VALID_TOKEN_HEADER,
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_user_can_read_own_chat(self, db, client_auth_enabled):
        own_video = Video(title="My Video", status="complete", owner_uid=FAKE_UID)
        db.add(own_video)
        await db.flush()
        video_id = own_video.id
        await db.commit()

        r = await client_auth_enabled.get(
            f"/api/videos/{video_id}/chat",
            headers=VALID_TOKEN_HEADER,
        )
        assert r.status_code == 200
        assert r.json() == []
