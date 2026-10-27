from io import BytesIO
from unittest.mock import patch
from zipfile import ZipFile

import pytest
from app.core.firebase_auth import require_firebase_user
from app.db.session import Base, get_db
from app.main import app
from app.models.video import SlideFrame, Video
from app.schemas.video import SlideFrameResponse, SlideListResponse
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DB = "sqlite+aiosqlite:///:memory:"


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


# helper to insert a video row and return it
async def make_video(db, title="Test Lecture"):
    video = Video(title=title, status="pending", owner_uid="test-user-1")
    db.add(video)
    await db.flush()
    return video


async def make_slide(db, video_id, start, end, frame_path=None, ocr_text=None):
    frame = SlideFrame(
        video_id=video_id,
        start_time=start,
        end_time=end,
        frame_path=frame_path,
        ocr_text=ocr_text,
    )
    db.add(frame)
    await db.flush()
    return frame


class TestSlideSchemas:
    def test_slide_frame_response_requires_id(self):
        with pytest.raises(ValidationError):
            SlideFrameResponse(start_time=0.0, end_time=5.0)  # type: ignore[call-arg]

    def test_slide_frame_response_requires_start_time(self):
        with pytest.raises(ValidationError):
            SlideFrameResponse(id=1, end_time=5.0)  # type: ignore[call-arg]

    def test_slide_frame_response_requires_end_time(self):
        with pytest.raises(ValidationError):
            SlideFrameResponse(id=1, start_time=0.0)  # type: ignore[call-arg]

    def test_slide_frame_response_nullable_fields(self):
        # ocr_text and frame_url are both optional
        frame = SlideFrameResponse(id=1, start_time=0.0, end_time=5.0)
        assert frame.ocr_text is None
        assert frame.frame_url is None

    def test_slide_list_response_total_matches_slides(self):
        slides = [
            SlideFrameResponse(id=i, start_time=float(i * 5), end_time=float(i * 5 + 5))
            for i in range(3)
        ]
        resp = SlideListResponse(video_id=1, total=3, slides=slides)
        assert resp.total == len(resp.slides)


class TestSlidesEndpoint:
    @pytest.mark.asyncio
    @patch("app.api.videos.StorageService")
    async def test_slides_returns_404_for_missing_video(self, mock_storage, client):
        r = await client.get("/api/videos/999/slides")
        assert r.status_code == 404

    @pytest.mark.asyncio
    @patch("app.api.videos.StorageService")
    async def test_slides_empty_when_no_frames(self, mock_storage, client, db):
        video = await make_video(db)
        r = await client.get(f"/api/videos/{video.id}/slides")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 0
        assert data["slides"] == []

    @pytest.mark.asyncio
    @patch("app.api.videos.StorageService")
    async def test_slides_returns_correct_shape(self, mock_storage, client, db):
        mock_storage.return_value.get_presigned_url.return_value = "http://minio/frame.jpg"
        video = await make_video(db)
        await make_slide(db, video.id, 0.0, 10.0, frame_path="slides/1/frame.jpg", ocr_text="Hello")

        r = await client.get(f"/api/videos/{video.id}/slides")
        assert r.status_code == 200
        data = r.json()
        assert data["video_id"] == video.id
        assert data["total"] == 1
        slide = data["slides"][0]
        assert slide["start_time"] == 0.0
        assert slide["end_time"] == 10.0
        assert slide["ocr_text"] == "Hello"
        assert slide["frame_url"] == "http://minio/frame.jpg"

    @pytest.mark.asyncio
    @patch("app.api.videos.StorageService")
    async def test_slides_pagination(self, mock_storage, client, db):
        mock_storage.return_value.get_presigned_url.return_value = "http://minio/x.jpg"
        video = await make_video(db)
        for i in range(3):
            await make_slide(db, video.id, float(i * 10), float(i * 10 + 10), frame_path="f.jpg")

        r = await client.get(f"/api/videos/{video.id}/slides?offset=1&limit=1")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 3  # total should reflect all frames, not just this page
        assert len(data["slides"]) == 1
        assert data["slides"][0]["start_time"] == 10.0

    @pytest.mark.asyncio
    @patch("app.api.videos.StorageService")
    async def test_download_slides_returns_zip(self, mock_storage, client, db):
        mock_storage.return_value.download_to_fileobj.side_effect = (
            lambda key, fileobj: fileobj.write(f"frame:{key}".encode())
        )
        video = await make_video(db)
        await make_slide(db, video.id, 0.0, 5.0, frame_path="slides/1.jpg")

        resp = await client.get(f"/api/videos/{video.id}/slides/download")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        assert 'attachment; filename="slides' in resp.headers["content-disposition"]

        buf = BytesIO(resp.content)
        with ZipFile(buf, "r") as archive:
            names = archive.namelist()
            assert len(names) == 1
            data = archive.read(names[0])
            assert data == b"frame:slides/1.jpg"

    @pytest.mark.asyncio
    @patch("app.api.videos.StorageService")
    async def test_download_slides_missing_frame_returns_404(self, mock_storage, client, db):
        video = await make_video(db)
        await make_slide(db, video.id, 0.0, 5.0, frame_path=None)

        resp = await client.get(f"/api/videos/{video.id}/slides/download")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    @patch("app.api.videos.StorageService")
    async def test_slides_invalid_time_range_returns_400(self, mock_storage, client, db):
        video = await make_video(db)
        r = await client.get(f"/api/videos/{video.id}/slides?start_time=10&end_time=5")
        assert r.status_code == 400

    @pytest.mark.asyncio
    @patch("app.api.videos.StorageService")
    async def test_slides_time_range_filters_correctly(self, mock_storage, client, db):
        mock_storage.return_value.get_presigned_url.return_value = "http://minio/x.jpg"
        video = await make_video(db)
        await make_slide(db, video.id, 0.0, 8.0, frame_path="a.jpg")  # no overlap with [10,25]
        await make_slide(db, video.id, 12.0, 20.0, frame_path="b.jpg")  # overlaps
        await make_slide(db, video.id, 30.0, 40.0, frame_path="c.jpg")  # no overlap

        r = await client.get(f"/api/videos/{video.id}/slides?start_time=10&end_time=25")
        assert r.status_code == 200
        data = r.json()
        assert len(data["slides"]) == 1
        assert data["slides"][0]["start_time"] == 12.0

    @pytest.mark.asyncio
    @patch("app.api.videos.StorageService")
    async def test_slides_presigned_url_fallback_on_error(self, mock_storage, client, db):
        mock_storage.return_value.get_presigned_url.side_effect = Exception("minio down")
        video = await make_video(db)
        await make_slide(db, video.id, 0.0, 10.0, frame_path="slides/raw/key.jpg")

        r = await client.get(f"/api/videos/{video.id}/slides")
        assert r.status_code == 200
        # falls back to raw path rather than crashing
        assert r.json()["slides"][0]["frame_url"] == "slides/raw/key.jpg"

    @pytest.mark.asyncio
    @patch("app.api.videos.StorageService")
    async def test_slides_frame_path_none_gives_null_url(self, mock_storage, client, db):
        video = await make_video(db)
        await make_slide(db, video.id, 0.0, 10.0, frame_path=None)

        r = await client.get(f"/api/videos/{video.id}/slides")
        assert r.status_code == 200
        assert r.json()["slides"][0]["frame_url"] is None
        mock_storage.return_value.get_presigned_url.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.api.videos.StorageService")
    async def test_slides_pending_video_returns_empty(self, mock_storage, client, db):
        video = await make_video(db)  # status defaults to pending
        r = await client.get(f"/api/videos/{video.id}/slides")
        assert r.status_code == 200
        assert r.json()["total"] == 0

    @pytest.mark.asyncio
    @patch("app.api.videos.StorageService")
    async def test_slides_large_offset_returns_empty(self, mock_storage, client, db):
        mock_storage.return_value.get_presigned_url.return_value = "http://minio/x.jpg"
        video = await make_video(db)
        await make_slide(db, video.id, 0.0, 10.0, frame_path="f.jpg")

        r = await client.get(f"/api/videos/{video.id}/slides?offset=999")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1  # total is still accurate
        assert data["slides"] == []


class TestSlidesIntegration:
    @pytest.mark.asyncio
    @patch("app.api.videos.StorageService")
    async def test_three_frames_returned_in_order(self, mock_storage, client, db):
        mock_storage.return_value.get_presigned_url.return_value = "http://minio/x.jpg"
        video = await make_video(db)
        # insert out of order to confirm ordering by start_time
        await make_slide(db, video.id, 20.0, 30.0, frame_path="c.jpg")
        await make_slide(db, video.id, 0.0, 10.0, frame_path="a.jpg")
        await make_slide(db, video.id, 10.0, 20.0, frame_path="b.jpg")

        r = await client.get(f"/api/videos/{video.id}/slides")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 3
        starts = [s["start_time"] for s in data["slides"]]
        assert starts == [0.0, 10.0, 20.0]

    @pytest.mark.asyncio
    @patch("app.api.videos.StorageService")
    async def test_time_range_overlap_integration(self, mock_storage, client, db):
        mock_storage.return_value.get_presigned_url.return_value = "http://minio/x.jpg"
        video = await make_video(db)
        await make_slide(db, video.id, 0.0, 9.0, frame_path="a.jpg")
        await make_slide(db, video.id, 10.0, 24.0, frame_path="b.jpg")
        await make_slide(db, video.id, 25.0, 35.0, frame_path="c.jpg")

        r = await client.get(f"/api/videos/{video.id}/slides?start_time=10&end_time=25")
        assert r.status_code == 200
        slides = r.json()["slides"]
        assert len(slides) == 1
        assert slides[0]["start_time"] == 10.0

    @pytest.mark.asyncio
    @patch("app.api.videos.StorageService")
    async def test_pagination_offset_and_limit(self, mock_storage, client, db):
        mock_storage.return_value.get_presigned_url.return_value = "http://minio/x.jpg"
        video = await make_video(db)
        for i in range(4):
            await make_slide(db, video.id, float(i * 10), float(i * 10 + 10), frame_path="f.jpg")

        r = await client.get(f"/api/videos/{video.id}/slides?offset=1&limit=1")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 4
        assert len(data["slides"]) == 1
        assert data["slides"][0]["start_time"] == 10.0
