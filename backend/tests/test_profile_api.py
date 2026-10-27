from datetime import datetime, timedelta, timezone

import pytest
from app.core.firebase_auth import require_firebase_user
from app.core.rate_limit import limiter
from app.db.session import Base, get_db
from app.main import app
from app.models.video import ProcessingStatus, Video
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DB = "sqlite+aiosqlite:///:memory:"


def reset_rate_limits():
    storage = limiter._storage
    if hasattr(storage, "storage"):
        storage.storage.clear()
    if hasattr(storage, "expirations"):
        storage.expirations.clear()
    if hasattr(storage, "events"):
        storage.events.clear()
    if hasattr(storage, "locks"):
        storage.locks.clear()


@pytest.fixture
async def db():
    engine = create_async_engine(TEST_DB)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess
    await engine.dispose()


@pytest.fixture
async def client(db):
    async def override():
        yield db

    app.dependency_overrides[get_db] = override
    reset_rate_limits()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    reset_rate_limits()
    app.dependency_overrides.clear()


@pytest.fixture
def auth_user():
    def set_user(uid: str):
        async def override_auth():
            return {"uid": uid}

        app.dependency_overrides[require_firebase_user] = override_auth

    yield set_user
    app.dependency_overrides.pop(require_firebase_user, None)


@pytest.fixture
async def seeded_profile_videos(db):
    now = datetime.now(timezone.utc)
    videos = [
        Video(
            title="Ready Lecture",
            owner_uid="user-1",
            status=ProcessingStatus.COMPLETE.value,
            duration=3600,
            created_at=now - timedelta(hours=3),
        ),
        Video(
            title="Processing Lecture",
            owner_uid="user-1",
            status=ProcessingStatus.TRANSCRIBING.value,
            duration=None,
            created_at=now - timedelta(hours=2),
        ),
        Video(
            title="Failed Lecture",
            owner_uid="user-1",
            status=ProcessingStatus.FAILED.value,
            duration=1200,
            created_at=now - timedelta(hours=1),
        ),
        Video(
            title="Other User Lecture",
            owner_uid="user-2",
            status=ProcessingStatus.COMPLETE.value,
            duration=9999,
            created_at=now,
        ),
    ]
    db.add_all(videos)
    await db.commit()
    return videos


class TestProfileSummary:
    @pytest.mark.asyncio
    async def test_returns_empty_summary_for_user_with_no_videos(self, client, auth_user):
        auth_user("user-empty")

        response = await client.get("/api/profile/me")

        assert response.status_code == 200
        assert response.json() == {
            "lecture_count": 0,
            "ready_lecture_count": 0,
            "processing_lecture_count": 0,
            "failed_lecture_count": 0,
            "total_duration_seconds": 0.0,
            "recent_uploads": [],
        }

    @pytest.mark.asyncio
    async def test_returns_owner_scoped_summary(self, client, auth_user, seeded_profile_videos):
        auth_user("user-1")

        response = await client.get("/api/profile/me")

        assert response.status_code == 200
        payload = response.json()
        assert payload["lecture_count"] == 3
        assert payload["ready_lecture_count"] == 1
        assert payload["processing_lecture_count"] == 1
        assert payload["failed_lecture_count"] == 1
        assert payload["total_duration_seconds"] == 4800.0
        assert [item["title"] for item in payload["recent_uploads"]] == [
            "Failed Lecture",
            "Processing Lecture",
            "Ready Lecture",
        ]


class TestProfileSettings:
    @pytest.mark.asyncio
    async def test_requires_authenticated_user(self, client):
        response = await client.get("/api/profile/settings")
        assert response.status_code == 401
        assert (
            "Missing Authorization header" in response.text
            or "Authenticated user id missing from token" in response.text
        )

    @pytest.mark.asyncio
    async def test_get_creates_defaults_for_user(self, client, auth_user):
        auth_user("user-settings-default")

        response = await client.get("/api/profile/settings")

        assert response.status_code == 200
        assert response.json() == {
            "uid": "user-settings-default",
            "theme_mode": "light",
            "background_mode": "animated",
            "card_style": "solid",
            "video_animation": 1,
            "autoplay_next": True,
            "pause_on_leave": True,
            "volume_default": 1.0,
            "muted_default": False,
            "preferred_language": "en",
            "timezone": None,
        }

    @pytest.mark.asyncio
    async def test_put_updates_and_get_returns_user_settings(self, client, auth_user):
        auth_user("user-settings-update")

        update_payload = {
            "theme_mode": "dark",
            "background_mode": "static",
            "card_style": "transparent",
            "video_animation": 6,
            "autoplay_next": False,
            "pause_on_leave": False,
            "volume_default": 0.4,
            "muted_default": True,
            "preferred_language": "en-GB",
            "timezone": "Europe/London",
        }

        put_response = await client.put("/api/profile/settings", json=update_payload)
        assert put_response.status_code == 200
        assert put_response.json() == {"uid": "user-settings-update", **update_payload}

        get_response = await client.get("/api/profile/settings")
        assert get_response.status_code == 200
        assert get_response.json() == {"uid": "user-settings-update", **update_payload}
