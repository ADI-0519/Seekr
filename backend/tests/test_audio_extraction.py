"""Unit tests for the AudioExtractor service.

These tests mock subprocess.run so ffmpeg / ffprobe are NOT required.
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from app.services.audio import (
    FFMPEG_CHANNELS,
    FFMPEG_CODEC,
    FFMPEG_SAMPLE_RATE,
    AudioExtractionError,
    AudioExtractor,
    AudioInfo,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def ffprobe_json(
    sample_rate: int = FFMPEG_SAMPLE_RATE,
    channels: int = FFMPEG_CHANNELS,
    duration: float = 10.0,
    codec: str = FFMPEG_CODEC,
) -> str:
    """Return fake ffprobe JSON output."""
    return json.dumps(
        {
            "streams": [
                {
                    "sample_rate": str(sample_rate),
                    "channels": channels,
                    "duration": str(duration),
                    "codec_name": codec,
                }
            ]
        }
    )


def mock_run_success(cmd, **kwargs):
    """Simulate successful ffmpeg / ffprobe calls."""
    mock = MagicMock()
    mock.returncode = 0
    mock.stderr = ""
    if cmd[0] == "ffprobe":
        mock.stdout = ffprobe_json()
    else:
        mock.stdout = ""
    return mock


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestExtractProduces16kHzMonoWav:
    """AC: output format verified (16 kHz mono WAV)."""

    @patch("app.services.audio.subprocess.run")
    def test_ffmpeg_command_has_correct_flags(self, mock_run, tmp_path):
        """Verify the ffmpeg command contains -ar 16000 -ac 1 -acodec pcm_s16le."""
        # Create a fake input file
        src = tmp_path / "input.mp4"
        src.write_bytes(b"fake-video")

        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

        extractor = AudioExtractor()
        wav_path = extractor.extract(str(src))

        # Inspect the command that was called
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "ffmpeg"
        assert "-ar" in call_args
        assert str(FFMPEG_SAMPLE_RATE) in call_args
        assert "-ac" in call_args
        assert str(FFMPEG_CHANNELS) in call_args
        assert "-acodec" in call_args
        assert FFMPEG_CODEC in call_args
        assert wav_path.endswith(".wav")

        # Cleanup temp
        if os.path.exists(wav_path):
            os.unlink(wav_path)

    @patch("app.services.audio.subprocess.run")
    def test_extract_returns_wav_file(self, mock_run, tmp_path):
        """Output path ends with .wav."""
        src = tmp_path / "lecture.mp4"
        src.write_bytes(b"data")

        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

        extractor = AudioExtractor()
        result = extractor.extract(str(src))
        assert result.endswith(".wav")

        if os.path.exists(result):
            os.unlink(result)


class TestExtractPreservesDuration:
    """AC: duration preserved."""

    def test_matching_duration_passes(self):
        extractor = AudioExtractor()
        info = AudioInfo(
            sample_rate=FFMPEG_SAMPLE_RATE,
            channels=FFMPEG_CHANNELS,
            duration=10.0,
            codec=FFMPEG_CODEC,
        )
        with patch.object(extractor, "probe", return_value=info):
            result = extractor.validate_output("/fake.wav", expected_duration=10.0)
        assert result.duration == 10.0

    def test_large_drift_raises(self):
        extractor = AudioExtractor()
        info = AudioInfo(
            sample_rate=FFMPEG_SAMPLE_RATE,
            channels=FFMPEG_CHANNELS,
            duration=80.0,
            codec=FFMPEG_CODEC,
        )
        with patch.object(extractor, "probe", return_value=info):
            with pytest.raises(AudioExtractionError, match="duration drift"):
                extractor.validate_output("/fake.wav", expected_duration=10.0)

    def test_small_drift_ok(self):
        extractor = AudioExtractor()
        info = AudioInfo(
            sample_rate=FFMPEG_SAMPLE_RATE,
            channels=FFMPEG_CHANNELS,
            duration=10.5,
            codec=FFMPEG_CODEC,
        )
        with patch.object(extractor, "probe", return_value=info):
            result = extractor.validate_output("/fake.wav", expected_duration=10.0)
        assert result.duration == 10.5


class TestCleanupDeletesTempFiles:
    """AC: temp file cleanup verified."""

    def test_cleanup_removes_existing_files(self):
        fd1, p1 = tempfile.mkstemp(suffix=".wav")
        os.close(fd1)
        fd2, p2 = tempfile.mkstemp(suffix=".mp4")
        os.close(fd2)

        assert os.path.exists(p1)
        assert os.path.exists(p2)

        AudioExtractor.cleanup(p1, p2)

        assert not os.path.exists(p1)
        assert not os.path.exists(p2)

    def test_cleanup_ignores_missing_files(self):
        """Should not raise for files that don't exist."""
        AudioExtractor.cleanup("/tmp/no-such-file-12345.wav")


class TestExtractRaisesOnFfmpegFailure:
    """Non-zero exit code should raise AudioExtractionError."""

    @patch("app.services.audio.subprocess.run")
    def test_nonzero_exit_code(self, mock_run, tmp_path):
        src = tmp_path / "bad.mp4"
        src.write_bytes(b"corrupted")

        mock_run.return_value = MagicMock(returncode=1, stderr="Error reading input", stdout="")

        extractor = AudioExtractor()
        with pytest.raises(AudioExtractionError, match="ffmpeg exited with code 1"):
            extractor.extract(str(src))

    @patch("app.services.audio.subprocess.run")
    def test_input_file_missing_raises(self, mock_run):
        extractor = AudioExtractor()
        with pytest.raises(AudioExtractionError, match="does not exist"):
            extractor.extract("/nonexistent/video.mp4")


class TestValidateOutputRejectsWrongFormat:
    """Validate catches wrong sample rate, channels, or codec."""

    def test_wrong_sample_rate(self):
        extractor = AudioExtractor()
        info = AudioInfo(sample_rate=44100, channels=1, duration=10.0, codec=FFMPEG_CODEC)
        with patch.object(extractor, "probe", return_value=info):
            with pytest.raises(AudioExtractionError, match="sample_rate"):
                extractor.validate_output("/fake.wav")

    def test_wrong_channels(self):
        extractor = AudioExtractor()
        info = AudioInfo(
            sample_rate=FFMPEG_SAMPLE_RATE, channels=2, duration=10.0, codec=FFMPEG_CODEC
        )
        with patch.object(extractor, "probe", return_value=info):
            with pytest.raises(AudioExtractionError, match="channels"):
                extractor.validate_output("/fake.wav")

    def test_wrong_codec(self):
        extractor = AudioExtractor()
        info = AudioInfo(sample_rate=FFMPEG_SAMPLE_RATE, channels=1, duration=10.0, codec="aac")
        with patch.object(extractor, "probe", return_value=info):
            with pytest.raises(AudioExtractionError, match="codec"):
                extractor.validate_output("/fake.wav")
