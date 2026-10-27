from unittest.mock import patch

import pytest
from app.core.firebase_auth import require_firebase_user
from app.db.session import Base, get_db
from app.main import app
from app.models.video import ProcessingJob, ProcessingStatus, Video
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

TEST_DB = "sqlite+aiosqlite:///:memory:"
pytestmark = pytest.mark.integration


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


@pytest.fixture
async def seeded_video(db):
    import os

    from app.services.storage import StorageService

    storage = StorageService()
    storage.ensure_bucket_exists()
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "sample.mp4")
    key = storage.generate_object_key(1, "sample.mp4")
    with open(fixture_path, "rb") as f:
        storage.upload_fileobj(f, key, content_type="video/mp4")

    v = Video(
        title="Test Lecture",
        status=ProcessingStatus.PENDING.value,
        storage_path=key,
        owner_uid="test-user-1",
    )

    db.add(v)
    await db.commit()
    await db.refresh(v)
    return v


def patch_task(video_id=None, video_data=None):
    from app.tasks import video_tasks

    sync_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(sync_engine)
    SyncTestSession = sessionmaker(bind=sync_engine)

    # seed the sync db with matching video if provided
    if video_id and video_data:
        sync_sess = SyncTestSession()
        v = Video(id=video_id, **video_data)
        sync_sess.add(v)
        sync_sess.commit()
        sync_sess.close()

    return (
        patch.object(video_tasks, "SyncSession", SyncTestSession),
        patch.object(video_tasks, "run_audio_extraction", return_value="audio/1/audio.wav"),
        patch.object(video_tasks, "run_slide_extraction", return_value=0),
        patch.object(video_tasks, "run_transcription"),
        patch.object(video_tasks, "run_segmentation", return_value=3),
        patch.object(video_tasks, "run_embedding"),
    )


class TestJobsTrigger:
    @pytest.mark.asyncio
    async def test_trigger_returns_202(self, client, seeded_video):
        video_data = {
            "title": seeded_video.title,
            "status": seeded_video.status,
            "storage_path": seeded_video.storage_path,
        }
        p1, p2, p3, p4, p5, p6 = patch_task(seeded_video.id, video_data)
        with p1, p2, p3, p4, p5, p6:
            resp = await client.post(f"/api/jobs/{seeded_video.id}")
        assert resp.status_code == 202
        data = resp.json()
        assert data["video_id"] == seeded_video.id
        assert "task_id" in data
        assert data["message"] == "Processing queued"

    @pytest.mark.asyncio
    async def test_trigger_nonexistent_video(self, client):
        resp = await client.post("/api/jobs/9999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_trigger_rejects_when_active_job_exists(self, client, db, seeded_video):
        db.add(
            ProcessingJob(
                video_id=seeded_video.id,
                task_id="already-running",
                status="running",
            )
        )
        await db.commit()

        resp = await client.post(f"/api/jobs/{seeded_video.id}")
        assert resp.status_code == 409


class TestJobsPolling:
    @pytest.mark.asyncio
    async def test_poll_no_job_returns_404(self, client, seeded_video):
        resp = await client.get(f"/api/jobs/{seeded_video.id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_poll_nonexistent_video(self, client):
        resp = await client.get("/api/jobs/9999")
        assert resp.status_code == 404


class TestJobsCancel:
    @pytest.mark.asyncio
    async def test_cancel_running_job_marks_job_and_video_cancelled(self, client, db, seeded_video):
        job = ProcessingJob(
            video_id=seeded_video.id,
            task_id="celery-task-1",
            status="running",
            current_stage=ProcessingStatus.TRANSCRIBING.value,
        )
        db.add(job)
        await db.commit()

        with patch("app.api.jobs.celery_app.control.revoke") as revoke_mock:
            resp = await client.post(f"/api/jobs/{seeded_video.id}/cancel")

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["status"] == "cancelled"
        revoke_mock.assert_called_once_with("celery-task-1", terminate=True)
        persisted_video = await db.get(Video, seeded_video.id)
        persisted_job = await db.get(ProcessingJob, job.id)
        assert persisted_video is not None
        assert persisted_video.status == ProcessingStatus.FAILED.value
        assert persisted_video.error_message == "Processing cancelled by user"
        assert persisted_job is not None
        assert persisted_job.status == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_terminal_job_rejected(self, client, db, seeded_video):
        job = ProcessingJob(
            video_id=seeded_video.id,
            task_id="celery-task-2",
            status="done",
        )
        db.add(job)
        await db.commit()

        resp = await client.post(f"/api/jobs/{seeded_video.id}/cancel")
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_cancel_job_without_task_id_rejected(self, client, db, seeded_video):
        job = ProcessingJob(
            video_id=seeded_video.id,
            task_id=None,
            status="running",
        )
        db.add(job)
        await db.commit()

        resp = await client.post(f"/api/jobs/{seeded_video.id}/cancel")
        assert resp.status_code == 409
