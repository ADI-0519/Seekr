from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

# Standardized audio parameters required for accurate AI transcription
FFMPEG_SAMPLE_RATE = 16000
FFMPEG_CHANNELS = 1
FFMPEG_CODEC = "pcm_s16le"
DURATION_TOLERANCE_SECS = 1.0


# Custom exception for media processing failures
class AudioExtractionError(Exception):
    pass


# Data structure holding verified audio metadata
@dataclass(frozen=True)
class AudioInfo:
    sample_rate: int
    channels: int
    duration: float
    codec: str


# Utility class to interface with ffmpeg for media manipulation
class AudioExtractor:
    # Strip video track and convert audio to 16kHz mono WAV format
    def extract(self, video_path: str) -> str:
        video_path_obj = Path(video_path)
        if not video_path_obj.is_file():
            raise AudioExtractionError(f"Input file does not exist: {video_path}")
        fd, wav_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-acodec",
            FFMPEG_CODEC,
            "-ar",
            str(FFMPEG_SAMPLE_RATE),
            "-ac",
            str(FFMPEG_CHANNELS),
            wav_path,
        ]
        log.info("Running ffmpeg: %s", " ".join(cmd))
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10-minute safety timeout
            )
        except subprocess.TimeoutExpired as exc:
            self.cleanup(wav_path)
            raise AudioExtractionError("ffmpeg timed out") from exc
        if result.returncode != 0:
            self.cleanup(wav_path)
            raise AudioExtractionError(
                f"ffmpeg exited with code {result.returncode}: {result.stderr[:500]}"
            )
        log.info("ffmpeg finished, WAV at %s", wav_path)
        return wav_path

    # Verify the extracted audio matches expected specifications and duration
    def validate_output(self, wav_path: str, expected_duration: float | None = None) -> AudioInfo:
        info = self.probe(wav_path)
        errors: list[str] = []
        if info.sample_rate != FFMPEG_SAMPLE_RATE:
            errors.append(f"sample_rate={info.sample_rate}, expected {FFMPEG_SAMPLE_RATE}")
        if info.channels != FFMPEG_CHANNELS:
            errors.append(f"channels={info.channels}, expected {FFMPEG_CHANNELS}")
        if info.codec != FFMPEG_CODEC:
            errors.append(f"codec={info.codec}, expected {FFMPEG_CODEC}")
        if expected_duration is not None:
            drift = abs(info.duration - expected_duration)
            tolerance = max(60.0, expected_duration * 0.05)
            if drift > tolerance:
                errors.append(
                    f"duration drift={drift:.2f}s (source={expected_duration:.2f}, "
                    f"output={info.duration:.2f}, tolerance={tolerance:.2f}s)"
                )
        if errors:
            raise AudioExtractionError("Output validation failed: " + "; ".join(errors))
        return info

    # Retrieve total video length in seconds using ffprobe
    def probe_video_duration(self, file_path: str) -> float:
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            file_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired as exc:
            raise AudioExtractionError("ffprobe timed out") from exc
        if result.returncode != 0:
            raise AudioExtractionError(
                f"ffprobe failed (rc={result.returncode}): {result.stderr[:300]}"
            )
        try:
            data = json.loads(result.stdout)
            return float(data["format"]["duration"])
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            raise AudioExtractionError(f"Could not parse video duration: {exc}") from exc

    # Generate a high-quality JPEG thumbnail image from a specific point in the video
    def extract_thumbnail(self, video_path: str, position_pct: float = 0.10) -> str:
        video_path_obj = Path(video_path)
        if not video_path_obj.is_file():
            raise AudioExtractionError(f"Input file does not exist: {video_path}")
        duration = self.probe_video_duration(video_path)
        seek_time = max(0, duration * position_pct)
        fd, jpg_path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            str(seek_time),
            "-i",
            str(video_path),
            "-vframes",
            "1",
            "-q:v",
            "2",
            jpg_path,
        ]
        log.info("Extracting thumbnail: %s", " ".join(cmd))
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired as exc:
            self.cleanup(jpg_path)
            raise AudioExtractionError("ffmpeg thumbnail timed out") from exc
        if result.returncode != 0:
            self.cleanup(jpg_path)
            raise AudioExtractionError(
                f"ffmpeg thumbnail failed (rc={result.returncode}): {result.stderr[:500]}"
            )
        # Verify the file was actually created and is non-empty
        if not os.path.isfile(jpg_path) or os.path.getsize(jpg_path) == 0:
            self.cleanup(jpg_path)
            raise AudioExtractionError("Thumbnail file is empty or missing")
        log.info("Thumbnail extracted at %.1fs -> %s", seek_time, jpg_path)
        return jpg_path

    # Delete temporary files from the filesystem
    @staticmethod
    def cleanup(*paths: str) -> None:
        for p in paths:
            try:
                os.unlink(p)
                log.debug("Cleaned up temp file: %s", p)
            except OSError:
                pass

    # Extract detailed stream metadata from an audio file
    @staticmethod
    def probe(file_path: str) -> AudioInfo:
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-select_streams",
            "a:0",
            file_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired as exc:
            raise AudioExtractionError("ffprobe timed out") from exc
        if result.returncode != 0:
            raise AudioExtractionError(
                f"ffprobe failed (rc={result.returncode}): {result.stderr[:300]}"
            )
        try:
            data = json.loads(result.stdout)
            stream = data["streams"][0]
        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            raise AudioExtractionError(f"Could not parse ffprobe output: {exc}") from exc
        return AudioInfo(
            sample_rate=int(stream.get("sample_rate", 0)),
            channels=int(stream.get("channels", 0)),
            duration=float(stream.get("duration", 0.0)),
            codec=stream.get("codec_name", ""),
        )
