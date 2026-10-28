import logging
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import yt_dlp

from app.core.config import get_settings
from app.core.log_safety import safe_exception_message, safe_url_for_log
from app.core.video_sources import (
    extract_kaltura_entry_id,
    extract_kaltura_partner_id,
    is_kaltura_url,
    is_supported_video_url,
    kaltura_referer,
)

log = logging.getLogger(__name__)


# Data structure for verified video assets and their technical specifications
@dataclass
class VideoMetadata:
    title: str
    duration: float | None
    has_audio: bool
    format: str | None
    original_url: str | None = None
    local_path: str | None = None


# Custom exception for file-level validation failures
class VideoValidationError(Exception):
    pass


# Custom exception for network-level download failures
class VideoDownloadError(Exception):
    pass


YouTubeDownloadError = VideoDownloadError

# Define strict limits and supported types for video ingestion
SUPPORTED_FORMATS = {".mp4", ".webm", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".m4v"}
VIDEO_CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    ".flv": "video/x-flv",
    ".wmv": "video/x-ms-wmv",
}
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
MAX_DURATION = 5 * 60 * 60  # 5 hours in seconds


def resolve_kaltura_url(url: str) -> str:
    entry_id = extract_kaltura_entry_id(url)
    if not entry_id:
        return url

    partner_id = extract_kaltura_partner_id(url) or get_settings().kaltura_default_partner_id

    # Extract the partner ID from the page source if available
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        match = re.search(r"partnerId[=:\x22\s]+(\d+)", html)
        if match:
            partner_id = match.group(1)
            log.info("discovered Kaltura partner ID: %s", partner_id)
    except Exception as e:
        log.warning(
            "could not fetch Kaltura page to discover partner ID, using default: %s: %s",
            type(e).__name__,
            safe_exception_message(e),
        )

    resolved = f"kaltura:{partner_id}:{entry_id}"
    log.info("resolved Kaltura URL to: %s", safe_url_for_log(resolved))
    return resolved


# Validate that a string is a well-formed URL from a supported source
def validate_url(url: str) -> bool:
    if not url:
        return False
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return False
    return is_supported_video_url(url)


# Define known file signatures to verify video files regardless of extension
VIDEO_MAGIC: list[tuple[int, bytes]] = [
    (4, b"ftyp"),  # MP4, M4V, MOV (ISO base media)
    (0, b"\x1a\x45\xdf\xa3"),  # MKV / WebM (EBML)
    (0, b"RIFF"),  # AVI
    (0, b"FLV"),  # FLV
    (0, b"\x30\x26\xb2\x75"),  # WMV / ASF
]


# Verify the file header matches known video binary signatures
def validate_file_mimetype(header: bytes) -> bool:
    for offset, sig in VIDEO_MAGIC:
        end = offset + len(sig)
        if len(header) >= end and header[offset:end] == sig:
            return True
    return False


# Check if the filename extension is present in the allowed formats list
def validate_file_extension(filename: str) -> bool:
    if not filename:
        return False
    ext = Path(filename).suffix.lower()
    return ext in SUPPORTED_FORMATS


# Map file extensions to their standard MIME type descriptors
def infer_video_content_type(filename: str) -> str | None:
    if not filename:
        return None
    return VIDEO_CONTENT_TYPES.get(Path(filename).suffix.lower())


# Determine total file size in bytes for a file-like object
def measure_file_size(fileobj) -> int | None:
    try:
        current_pos = fileobj.tell()
        fileobj.seek(0, os.SEEK_END)
        size = fileobj.tell()
        fileobj.seek(current_pos)
        return int(size)
    except (AttributeError, OSError, ValueError):
        return None


# Use ffprobe to detect the presence of at least one audio stream
def check_file_has_audio(filepath: str) -> bool:
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "csv=p=0",
            filepath,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return bool(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        log.warning("ffprobe check failed: %s: %s", type(e).__name__, safe_exception_message(e))
        return True  # assume audio present if we cant check


# Use ffprobe to extract the total duration of the media file in seconds
def get_video_duration(filepath: str) -> float | None:
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            filepath,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.stdout.strip():
            return float(result.stdout.strip())
    except Exception as e:
        log.warning("couldnt get duration: %s: %s", type(e).__name__, safe_exception_message(e))
    return None


# Enforce all technical constraints on a locally saved file upload
def validate_uploaded_file(file_path: str, original_filename: str) -> VideoMetadata:
    if not os.path.exists(file_path):
        raise VideoValidationError("File not found")

    if not validate_file_extension(original_filename):
        ext = Path(original_filename).suffix.lower()
        raise VideoValidationError(f"Unsupported format: {ext}")

    size = os.path.getsize(file_path)
    if size == 0:
        raise VideoValidationError("File is empty")
    if size > MAX_FILE_SIZE:
        raise VideoValidationError("File too large (max 2GB)")

    has_audio = check_file_has_audio(file_path)
    if not has_audio:
        raise VideoValidationError("Video has no audio track")

    duration = get_video_duration(file_path)
    if duration and duration > MAX_DURATION:
        raise VideoValidationError("Video too long (max 5 hours)")

    return VideoMetadata(
        title=Path(original_filename).stem,
        duration=duration,
        has_audio=has_audio,
        format=Path(original_filename).suffix.lower(),
        local_path=file_path,
    )


# Service class to handle remote video downloads and metadata extraction
class VideoDownloader:
    def __init__(self, download_dir: str | None = None, cookies_path: str | None = None):
        self.download_dir = download_dir or tempfile.mkdtemp(prefix="seekr_")
        self.cookies_path = cookies_path
        os.makedirs(self.download_dir, exist_ok=True)

    # Configure base options for yt-dlp including referer and cookie headers
    def base_opts(self, url: str) -> dict:
        opts: dict = {
            "quiet": True,
            "no_warnings": True,
        }
        if is_kaltura_url(url):
            if self.cookies_path:
                opts["cookiefile"] = self.cookies_path
            referer = kaltura_referer(url)
            if referer:
                opts["http_headers"] = {"Referer": referer}
        return opts

    # Retrieve video information from the remote source without downloading
    def extract_metadata(self, url: str) -> dict:
        resolved_url = resolve_kaltura_url(url) if is_kaltura_url(url) else url
        opts = {**self.base_opts(url), "extract_flat": False}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(resolved_url, download=False)
                if info is None:
                    raise VideoDownloadError("No video info returned")
                return dict(info)
        except yt_dlp.DownloadError as e:
            err = str(e).lower()
            if "private" in err or "unavailable" in err:
                raise VideoDownloadError("Video is not accessible.")
            if "login" in err or "403" in err or "401" in err:
                raise VideoDownloadError(
                    "Authentication required. Please upload valid cookies for this source."
                )
            raise VideoDownloadError("Download failed while fetching video metadata.")

    # Execute the video download and verify the resulting local file
    def download(self, url: str) -> VideoMetadata:
        resolved_url = resolve_kaltura_url(url) if is_kaltura_url(url) else url
        info = self.extract_metadata(url)

        title = info.get("title", "untitled")
        duration = info.get("duration")

        if duration and duration > MAX_DURATION:
            raise VideoValidationError(f"Video too long ({duration}s, max {MAX_DURATION}s)")

        safe_title = re.sub(r"[^\w\s-]", "", title)[:100]
        output_template = os.path.join(self.download_dir, f"{safe_title}.%(ext)s")

        opts = {
            **self.base_opts(url),
            "format": "bv*+ba/b"
            if is_kaltura_url(url)
            else "bestvideo[vcodec^=avc][ext=mp4]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": output_template,
            "quiet": False,
            "no_warnings": False,
            "merge_output_format": "mp4",
            "postprocessors": [],
            "noplaylist": True,
            "socket_timeout": 30,
            "retries": 10 if is_kaltura_url(url) else 3,
            "fragment_retries": 10 if is_kaltura_url(url) else 3,
        }

        if is_kaltura_url(url):
            opts["concurrent_fragment_downloads"] = 4

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([resolved_url])
        except yt_dlp.DownloadError as e:
            log.error("yt-dlp error: %s: %s", type(e).__name__, safe_exception_message(e))
            err = str(e).lower()
            if "login" in err or "403" in err or "401" in err:
                raise VideoDownloadError(
                    "Authentication required. Please upload valid cookies for this source."
                )
            raise VideoDownloadError("Download failed while fetching the video.")

        # Locate the downloaded file within the temporary directory
        downloaded_path = None
        for f in os.listdir(self.download_dir):
            if f.endswith((".mp4", ".webm", ".mkv")):
                downloaded_path = os.path.join(self.download_dir, f)
                break

        if not downloaded_path or not os.path.exists(downloaded_path):
            raise VideoDownloadError("Download completed but file not found")

        has_audio = check_file_has_audio(downloaded_path)
        if not has_audio:
            raise VideoValidationError("Downloaded video has no audio")

        actual_duration = get_video_duration(downloaded_path)

        return VideoMetadata(
            title=title,
            duration=actual_duration or duration,
            has_audio=has_audio,
            format=".mp4",
            original_url=url,
            local_path=downloaded_path,
        )

    # Delete all local files and the temporary download directory
    def cleanup(self):
        if self.download_dir and os.path.exists(self.download_dir):
            try:
                shutil.rmtree(self.download_dir)
            except Exception as e:
                log.warning("cleanup failed: %s: %s", type(e).__name__, safe_exception_message(e))


YouTubeDownloader = VideoDownloader


# High-level entry point to fetch a video from a URL with error handling
def acquire_from_url(
    url: str, output_dir: str | None = None, cookies_path: str | None = None
) -> VideoMetadata:
    if not validate_url(url):
        raise VideoValidationError("Invalid or unsupported URL")
    downloader = VideoDownloader(output_dir, cookies_path=cookies_path)
    try:
        return downloader.download(url)
    except Exception:
        downloader.cleanup()
        raise


acquire_from_youtube = acquire_from_url
