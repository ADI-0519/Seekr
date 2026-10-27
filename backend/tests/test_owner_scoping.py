from unittest.mock import patch

import pytest
from app.core.firebase_auth import require_firebase_user
from app.core.rate_limit import limiter
from app.db.session import Base, get_db
from app.main import app
from app.models.video import ProcessingJob, ProcessingStatus, Video
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
async def seeded_videos(db):
    mine = Video(title="Mine", owner_uid="user-1", status=ProcessingStatus.COMPLETE.value)
    theirs = Video(title="Theirs", owner_uid="user-2", status=ProcessingStatus.COMPLETE.value)
    db.add_all([mine, theirs])
    await db.flush()

    db.add(
        ProcessingJob(
            video_id=theirs.id,
            task_id="foreign-job-1",
            status="running",
        )
    )
    await db.commit()

    return {"mine": mine, "theirs": theirs}


class TestVideoOwnerScoping:
    @pytest.mark.asyncio
    async def test_list_only_returns_authenticated_owner_videos(
        self, client, auth_user, seeded_videos
    ):
        auth_user("user-1")

        response = await client.get("/api/videos/")

        assert response.status_code == 200
        payload = response.json()
        assert [item["id"] for item in payload] == [seeded_videos["mine"].id]

    @pytest.mark.asyncio
    async def test_get_other_users_video_returns_404(self, client, auth_user, seeded_videos):
        auth_user("user-1")

        response = await client.get(f"/api/videos/{seeded_videos['theirs'].id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_other_users_video_returns_404(self, client, auth_user, seeded_videos, db):
        auth_user("user-1")

        response = await client.delete(f"/api/videos/{seeded_videos['theirs'].id}")

        assert response.status_code == 404
        assert await db.get(Video, seeded_videos["theirs"].id) is not None

    @pytest.mark.asyncio
    @patch("app.api.videos.run_query")
    async def test_query_other_users_video_returns_404(
        self,
        run_query_mock,
        client,
        auth_user,
        seeded_videos,
    ):
        auth_user("user-1")

        response = await client.post(
            f"/api/videos/{seeded_videos['theirs'].id}/query",
            json={"query": "test", "mode": "retrieval", "top_k": 5},
        )

        assert response.status_code == 404
        run_query_mock.delay.assert_not_called()


class TestJobOwnerScoping:
    @pytest.mark.asyncio
    async def test_poll_other_users_job_returns_404(self, client, auth_user, seeded_videos):
        auth_user("user-1")

        response = await client.get(f"/api/jobs/{seeded_videos['theirs'].id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    @patch("app.api.jobs.celery_app.control.revoke")
    async def test_cancel_other_users_job_returns_404(
        self,
        revoke_mock,
        client,
        auth_user,
        seeded_videos,
        db,
    ):
        auth_user("user-1")

        response = await client.post(f"/api/jobs/{seeded_videos['theirs'].id}/cancel")

        assert response.status_code == 404
        revoke_mock.assert_not_called()
        assert await db.get(Video, seeded_videos["theirs"].id) is not None
