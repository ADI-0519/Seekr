"""Integration test: ingest → extract → WAV stored and readable by transcription stage.

Requires: ffmpeg installed, storage env vars set (MinIO or similar).
Skipped automatically if either is unavailable.
"""

import io
import os
import shutil
import tempfile
import wave
from unittest.mock import patch

import pytest
from app.core.config import get_settings
from app.db.session import Base
from app.models.video import ProcessingStatus, Video
from app.services.audio import AudioExtractor
from app.services.storage import StorageService
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# ---------------------------------------------------------------------------
# Skip guards
# ---------------------------------------------------------------------------


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def resolve_endpoint_url() -> str | None:
    endpoint = os.getenv("STORAGE_ENDPOINT_URL")
    if not endpoint:
        return None
    if endpoint.startswith("http://minio:"):
        return endpoint.replace("http://minio:", "http://localhost:", 1)
    if endpoint.startswith("https://minio:"):
        return endpoint.replace("https://minio:", "https://localhost:", 1)
    return endpoint


def create_synthetic_wav(
    path: str, duration: float = 0.5, sample_rate: int = 44100, channels: int = 2
) -> None:
    """Create a tiny valid WAV file with sine-wave-ish data."""
    n_frames = int(sample_rate * duration)
    with wave.open(path, "w") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        # Write simple data (just zeros — valid audio)
        wf.writeframes(b"\x00\x00" * channels * n_frames)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sync_db():
    """In-memory SQLite DB with schema."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    yield session
    session.close()
    engine.dispose()


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestEndToEndExtractAndStore:
    """AC: end-to-end ingest → extract → WAV stored and readable by transcription stage."""

    def test_full_pipeline(self, sync_db: Session, monkeypatch, tmp_path):
        if not ffmpeg_available():
            pytest.skip("ffmpeg/ffprobe not installed")

        endpoint_url = resolve_endpoint_url()
        if not endpoint_url:
            pytest.skip("STORAGE_ENDPOINT_URL not set")

        required = ["STORAGE_BUCKET", "STORAGE_ACCESS_KEY_ID", "STORAGE_SECRET_ACCESS_KEY"]
        if any(not os.getenv(name) for name in required):
            pytest.skip("Storage credentials not set")

        monkeypatch.setenv("STORAGE_ENDPOINT_URL", endpoint_url)
        get_settings.cache_clear()

        # 1. Create a synthetic source WAV (44.1 kHz stereo)
        src_wav = str(tmp_path / "source.wav")
        create_synthetic_wav(src_wav, duration=0.5, sample_rate=44100, channels=2)

        # 2. Wrap it in an MP4 container using ffmpeg
        src_mp4 = str(tmp_path / "source.mp4")
        import subprocess

        result = subprocess.run(
            ["ffmpeg", "-y", "-i", src_wav, "-c:a", "aac", src_mp4],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.skip(f"Could not create test MP4: {result.stderr[:200]}")

        # 3. Upload MP4 to object storage (simulates ingest stage / SKR-006)
        storage = StorageService()
        storage.ensure_bucket_exists()
        video_key = storage.generate_object_key(video_id=999, filename="source.mp4")
        with open(src_mp4, "rb") as f:
            storage.upload_fileobj(f, video_key, content_type="video/mp4")

        # 4. Create a Video row
        video = Video(
            id=999,
            title="Integration Test Video",
            storage_path=video_key,
            status=ProcessingStatus.PENDING.value,
        )
        sync_db.add(video)
        sync_db.commit()

        # 5. Run audio extraction (the function under test)
        from app.tasks.video_tasks import run_audio_extraction

        # Patch SyncSession / StorageService inside the task to use our test DB / real storage
        # Note: We must patch where the class is defined because it is imported locally inside the function
        with patch("app.services.storage.StorageService", return_value=storage):
            audio_key = run_audio_extraction(sync_db, video_id=999)

        # 6. Assert: audio_path is set in DB
        sync_db.refresh(video)
        assert video.audio_path is not None
        assert video.audio_path == audio_key
        assert audio_key.startswith("audio/")

        # 7. Assert: WAV is downloadable from storage
        output = io.BytesIO()
        storage.download_to_fileobj(audio_key, output)
        output.seek(0)
        assert len(output.getvalue()) > 0

        # 8. Assert: Downloaded WAV is 16 kHz mono
        extractor = AudioExtractor()
        # Write to temp file so we can probe it
        fd, probe_path = tempfile.mkstemp(suffix=".wav")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(output.getvalue())
            info = extractor.validate_output(probe_path)
            assert info.sample_rate == 16000
            assert info.channels == 1
            assert info.codec == "pcm_s16le"
            # Duration should be approximately 0.5s
            assert abs(info.duration - 0.5) < 1.0
        finally:
            extractor.cleanup(probe_path)
