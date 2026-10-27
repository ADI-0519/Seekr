import io
from unittest.mock import patch

import pytest
from app.api.videos import resolve_upload_size
from app.core.firebase_auth import require_firebase_user
from app.core.rate_limit import limiter
from app.db.session import Base, get_db
from app.main import app
from app.models.video import (
    Chunk,
    ProcessingJob,
    Segment,
    Sentence,
    SlideFrame,
    TranscriptWord,
    Video,
)
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.datastructures import UploadFile

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

    factory = async_sessionmaker(engine, class_=AsyncSession)
    async with factory() as sess:
        yield sess
    await engine.dispose()


@pytest.fixture
async def client(db):
    def override():
        yield db

    app.dependency_overrides[get_db] = override
    reset_rate_limits()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    reset_rate_limits()
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def auth_user():
    async def override_auth():
        return {"uid": "test-user-1", "email": "test@example.com"}

    app.dependency_overrides[require_firebase_user] = override_auth
    yield
    app.dependency_overrides.pop(require_firebase_user, None)


class TestHealth:
    @pytest.mark.asyncio
    async def test_returns_ok(self, client):
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestVideos:
    @pytest.mark.asyncio
    async def test_list_empty(self, client):
        r = await client.get("/api/videos/")
        assert r.status_code == 200
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_not_found(self, client):
        r = await client.get("/api/videos/999")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_requires_file(self, client):
        r = await client.post("/api/videos/upload", data={"title": "Test"})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_rejects_unsupported_format(self, client):
        file_content = b"not a video"
        files = {"file": ("document.txt", io.BytesIO(file_content), "text/plain")}
        r = await client.post(
            "/api/videos/upload",
            data={"title": "Test"},
            files=files,
        )
        assert r.status_code == 400
        assert "Unsupported" in r.json()["detail"]

    @pytest.mark.asyncio
    @patch("app.api.videos.process_video")
    @patch("app.api.videos.StorageService")
    async def test_upload_saves_authenticated_owner_uid(
        self, mock_storage_service, mock_task, client, db
    ):
        async def override_auth():
            return {"uid": "user-upload-1"}

        app.dependency_overrides[require_firebase_user] = override_auth
        storage = mock_storage_service.return_value
        storage.generate_object_key.return_value = "videos/1/test.mp4"
        mock_task.apply_async = lambda *_, **__: type("Result", (), {"id": "task-upload"})()

        files = {
            "file": (
                "lecture.mp4",
                io.BytesIO(b"\x00\x00\x00\x18ftypisom" + b"\x00" * 64),
                "text/plain",
            )
        }

        try:
            response = await client.post(
                "/api/videos/upload",
                data={"title": "Owned Upload"},
                files=files,
            )
        finally:
            app.dependency_overrides.pop(require_firebase_user, None)

        assert response.status_code == 200
        video = await db.get(Video, response.json()["id"])
        assert video is not None
        assert video.owner_uid == "user-upload-1"
        mock_storage_service.return_value.upload_fileobj.assert_called_once()
        assert (
            mock_storage_service.return_value.upload_fileobj.call_args.kwargs["content_type"]
            == "video/mp4"
        )

    @pytest.mark.asyncio
    @patch("app.api.videos.resolve_upload_size", return_value=3 * 1024 * 1024 * 1024)
    async def test_upload_rejects_when_resolved_size_exceeds_limit(self, _mock_size, client):
        files = {
            "file": (
                "lecture.mp4",
                io.BytesIO(b"\x00\x00\x00\x18ftypisom" + b"\x00" * 64),
                "video/mp4",
            )
        }

        response = await client.post(
            "/api/videos/upload",
            data={"title": "Too Big"},
            files=files,
        )

        assert response.status_code == 400
        assert "maximum allowed size" in response.json()["detail"]

    @pytest.mark.asyncio
    @patch("app.api.videos.QdrantService")
    @patch("app.api.videos.StorageService")
    async def test_delete_video_removes_video_and_related_records(
        self, mock_storage_service, mock_qdrant_service, client, db
    ):
        video = Video(
            title="Delete Me",
            status="complete",
            storage_path="videos/1/source.mp4",
            owner_uid="test-user-1",
        )
        db.add(video)
        await db.flush()
        db.add_all(
            [
                SlideFrame(
                    video_id=video.id,
                    frame_path="slides/1/frame-1.jpg",
                    start_time=0.0,
                    end_time=1.0,
                ),
                Sentence(
                    video_id=video.id,
                    text="Sentence",
                    start_time=0.0,
                    end_time=1.0,
                ),
                Segment(
                    video_id=video.id,
                    title="Segment",
                    summary=None,
                    start_time=0.0,
                    end_time=1.0,
                ),
                TranscriptWord(
                    video_id=video.id,
                    word="Delete",
                    start_time=0.0,
                    end_time=0.2,
                    probability=0.95,
                ),
                Chunk(
                    video_id=video.id,
                    text="Chunk",
                    start_time=0.0,
                    end_time=1.0,
                ),
                ProcessingJob(
                    video_id=video.id,
                    status="done",
                ),
            ]
        )
        video_id = video.id
        await db.commit()

        storage = mock_storage_service.return_value
        qdrant = mock_qdrant_service.return_value

        response = await client.delete(f"/api/videos/{video_id}")

        assert response.status_code == 204
        assert await db.get(Video, video_id) is None
        for model in (SlideFrame, Sentence, Segment, TranscriptWord, Chunk, ProcessingJob):
            remaining = await db.execute(select(model).where(model.video_id == video_id))
            assert remaining.scalars().all() == []
        assert storage.delete_object.call_count == 2
        qdrant.delete_video_points.assert_called_once_with(video_id)

    @pytest.mark.asyncio
    @patch("app.api.videos.QdrantService")
    async def test_qdrant_health_does_not_leak_internal_error(self, mock_qdrant_service, client):
        mock_qdrant_service.side_effect = RuntimeError(
            "failed for https://qdrant.local?api_key=super-secret"
        )

        response = await client.get("/api/videos/qdrant/health")

        assert response.status_code == 503
        assert response.json()["detail"] == "Qdrant is unavailable right now."

    @pytest.mark.asyncio
    async def test_playback_position_roundtrip(self, client, db):
        video = Video(
            title="Playback Test",
            status="complete",
            owner_uid="test-user-1",
            duration=300,
        )
        db.add(video)
        await db.flush()
        video_id = video.id
        await db.commit()

        put_response = await client.put(
            f"/api/videos/{video_id}/playback",
            json={"position_seconds": 81.5},
        )
        assert put_response.status_code == 200
        assert put_response.json()["position_seconds"] == 81.5

        get_response = await client.get(f"/api/videos/{video_id}/playback")
        assert get_response.status_code == 200
        assert get_response.json()["position_seconds"] == 81.5

    @pytest.mark.asyncio
    async def test_playback_position_clamped_to_duration(self, client, db):
        video = Video(
            title="Playback Clamp",
            status="complete",
            owner_uid="test-user-1",
            duration=100,
        )
        db.add(video)
        await db.flush()
        video_id = video.id
        await db.commit()

        response = await client.put(
            f"/api/videos/{video_id}/playback",
            json={"position_seconds": 250},
        )
        assert response.status_code == 200
        assert response.json()["position_seconds"] == 100


class TestYouTubeSubmit:
    @pytest.mark.asyncio
    @patch("app.api.videos.process_video")
    async def test_submit_saves_authenticated_owner_uid(self, mock_task, client, db):
        async def override_auth():
            return {"uid": "user-auth-1"}

        app.dependency_overrides[require_firebase_user] = override_auth
        mock_task.apply_async = lambda *_, **__: type("Result", (), {"id": "test-task-id"})()

        try:
            r = await client.post(
                "/api/videos/youtube",
                json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
            )
        finally:
            app.dependency_overrides.pop(require_firebase_user, None)

        assert r.status_code == 201
        video = await db.get(Video, r.json()["id"])
        assert video is not None
        assert video.owner_uid == "user-auth-1"


class TestUploadHelpers:
    def test_resolve_upload_size_uses_measured_length_when_size_missing(self):
        upload = UploadFile(filename="lecture.mp4", file=io.BytesIO(b"0123456789"), size=None)

        assert resolve_upload_size(upload) == 10
        assert upload.file.tell() == 0

    @pytest.mark.asyncio
    @patch("app.api.videos.process_video")
    async def test_submit_valid_url(self, mock_task, client):
        mock_task.apply_async = lambda *_, **__: type("Result", (), {"id": "test-task-id"})()

        r = await client.post(
            "/api/videos/youtube",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["youtube_url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    @patch("app.api.videos.process_video")
    async def test_submit_with_custom_title(self, mock_task, client):
        mock_task.apply_async = lambda *_, **__: type("Result", (), {"id": "test-task-id"})()

        r = await client.post(
            "/api/videos/youtube",
            json={
                "url": "https://youtu.be/dQw4w9WgXcQ",
                "title": "My Custom Title",
            },
        )
        assert r.status_code == 201
        assert r.json()["title"] == "My Custom Title"

    @pytest.mark.asyncio
    async def test_submit_invalid_url(self, client):
        r = await client.post(
            "/api/videos/youtube",
            json={"url": "https://vimeo.com/12345"},
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_empty_url(self, client):
        r = await client.post(
            "/api/videos/youtube",
            json={"url": ""},
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    @patch("app.api.videos.process_video")
    async def test_submit_short_url_format(self, mock_task, client):
        mock_task.apply_async = lambda *_, **__: type("Result", (), {"id": "test-task-id"})()

        r = await client.post(
            "/api/videos/youtube",
            json={"url": "https://youtu.be/dQw4w9WgXcQ"},
        )
        assert r.status_code == 201


class TestUrlDeduplication:
    @pytest.mark.asyncio
    @patch("app.api.videos.process_video")
    async def test_duplicate_url_for_different_owner_creates_new_video(self, mock_task, client, db):
        from app.models.video import ProcessingStatus

        async def auth_user_one():
            return {"uid": "user-1"}

        async def auth_user_two():
            return {"uid": "user-2"}

        mock_task.apply_async = lambda *_, **__: type("Result", (), {"id": "task-1"})()
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        app.dependency_overrides[require_firebase_user] = auth_user_one
        r1 = await client.post("/api/videos/youtube", json={"url": url})
        assert r1.status_code == 201

        video = await db.get(Video, r1.json()["id"])
        assert video is not None
        video.status = ProcessingStatus.COMPLETE.value
        await db.commit()

        app.dependency_overrides[require_firebase_user] = auth_user_two
        try:
            r2 = await client.post("/api/videos/youtube", json={"url": url})
        finally:
            app.dependency_overrides.pop(require_firebase_user, None)

        assert r2.status_code == 201
        assert r2.json()["id"] != r1.json()["id"]

    @pytest.mark.asyncio
    @patch("app.api.videos.process_video")
    async def test_duplicate_url_returns_existing(self, mock_task, client, db):
        from unittest.mock import MagicMock

        from app.models.video import ProcessingStatus, Video

        mock_apply = MagicMock(return_value=type("Result", (), {"id": "task-1"})())
        mock_task.apply_async = mock_apply

        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        r1 = await client.post("/api/videos/youtube", json={"url": url})
        assert r1.status_code == 201
        video_id = r1.json()["id"]

        video = await db.get(Video, video_id)
        video.status = ProcessingStatus.COMPLETE.value
        await db.commit()

        r2 = await client.post("/api/videos/youtube", json={"url": url})

        assert r2.status_code == 200
        assert r2.json()["id"] == video_id
        assert r2.json()["from_cache"] is True
        assert mock_apply.call_count == 1  # only the first submission triggered a job

    @pytest.mark.asyncio
    @patch("app.api.videos.process_video")
    async def test_different_urls_both_processed(self, mock_task, client):
        mock_task.apply_async = lambda *_, **__: type("Result", (), {"id": "task-x"})()

        r1 = await client.post(
            "/api/videos/youtube",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
        )
        r2 = await client.post(
            "/api/videos/youtube",
            json={"url": "https://www.youtube.com/watch?v=9bZkp7q19f0"},
        )

        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["id"] != r2.json()["id"]

    @pytest.mark.asyncio
    @patch("app.api.videos.process_video")
    async def test_failed_url_gets_reprocessed(self, mock_task, client, db):
        from app.models.video import ProcessingStatus, Video

        mock_task.apply_async = lambda *_, **__: type("Result", (), {"id": "task-y"})()

        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        r1 = await client.post("/api/videos/youtube", json={"url": url})
        assert r1.status_code == 201

        # mark as failed rather than complete
        video = await db.get(Video, r1.json()["id"])
        video.status = ProcessingStatus.FAILED.value
        await db.commit()

        r2 = await client.post("/api/videos/youtube", json={"url": url})
        assert r2.status_code == 201
        # should be a fresh video, not the failed one
        assert r2.json()["id"] != r1.json()["id"]
