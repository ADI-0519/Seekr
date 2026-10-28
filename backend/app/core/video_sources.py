import re
from urllib.parse import urlparse

from app.core.config import get_settings

YOUTUBE_PATTERNS = (
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})"),
)

KALTURA_ENTRY_PATTERNS = (
    re.compile(r"/browseandembed/index/media-redirect/entryid/([a-zA-Z0-9_]+)"),
    re.compile(r"/entryId/([a-zA-Z0-9_]+)"),
)
KALTURA_PARTNER_PATTERN = re.compile(r"/p/(\d+)(?:/|$)")


def _host(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return ""
    return (parsed.hostname or "").lower()


def is_youtube_url(url: str) -> bool:
    if not url or _host(url) not in {"youtube.com", "www.youtube.com", "youtu.be", "www.youtu.be"}:
        return False
    return any(pattern.match(url) for pattern in YOUTUBE_PATTERNS)


def extract_youtube_id(url: str) -> str | None:
    if not url or not _host(url):
        return None
    for pattern in YOUTUBE_PATTERNS:
        match = pattern.match(url)
        if match:
            return match.group(1)
    return None


def is_kaltura_url(url: str) -> bool:
    host = _host(url) if url else ""
    if not host:
        return False

    settings = get_settings()
    allowed_custom_hosts = {item.lower() for item in settings.kaltura_allowed_hosts}
    if not (host == "kaltura.com" or host.endswith(".kaltura.com") or host in allowed_custom_hosts):
        return False

    return any(pattern.search(urlparse(url).path) for pattern in KALTURA_ENTRY_PATTERNS)


def extract_kaltura_entry_id(url: str) -> str | None:
    if not is_kaltura_url(url):
        return None
    path = urlparse(url).path
    for pattern in KALTURA_ENTRY_PATTERNS:
        match = pattern.search(path)
        if match:
            return match.group(1)
    return None


def extract_kaltura_partner_id(url: str) -> str | None:
    if not is_kaltura_url(url):
        return None
    match = KALTURA_PARTNER_PATTERN.search(urlparse(url).path)
    return match.group(1) if match else None


def kaltura_referer(url: str) -> str | None:
    if not is_kaltura_url(url):
        return None
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}/"


def is_supported_video_url(url: str) -> bool:
    return is_youtube_url(url) or is_kaltura_url(url)
