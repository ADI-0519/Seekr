import re
from subprocess import TimeoutExpired
from urllib.parse import urlsplit, urlunsplit

_SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?i)\b("
    r"token|access_token|refresh_token|id_token|api_key|apikey|"
    r"password|secret|signature|sig|ks|x-amz-signature|x-amz-security-token|x-amz-credential"
    r")\s*[:=]\s*([^\s,;]+)"
)
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._=-]+")
_AUTH_HEADER_RE = re.compile(r"(?i)\bauthorization\s*:\s*bearer\s+[^\s,;]+")
_URL_RE = re.compile(r"https?://[^\s'\"<>]+")


def truncate(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 3].rstrip() + "..."


def safe_url_for_log(url: str | None, max_length: int = 160) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""

    if raw.startswith("kaltura:"):
        return truncate(raw, max_length)

    parts = urlsplit(raw)
    if not parts.scheme or not parts.netloc:
        return truncate(raw.split("?", 1)[0], max_length)

    host = parts.hostname or parts.netloc
    if parts.port:
        host = f"{host}:{parts.port}"

    sanitized = urlunsplit((parts.scheme, host, parts.path, "", ""))
    return truncate(sanitized, max_length)


def sanitize_text(value: str | None, max_length: int = 200) -> str:
    text = (value or "").strip()
    if not text:
        return ""

    text = _URL_RE.sub(lambda match: safe_url_for_log(match.group(0)), text)
    text = _AUTH_HEADER_RE.sub("Authorization: Bearer [redacted]", text)
    text = _BEARER_RE.sub("Bearer [redacted]", text)
    text = _SENSITIVE_ASSIGNMENT_RE.sub(r"\1=[redacted]", text)
    return truncate(text, max_length)


def safe_exception_message(
    exc: Exception | BaseException, fallback: str = "Operation failed.", max_length: int = 200
) -> str:
    if isinstance(exc, (TimeoutExpired, TimeoutError)):
        return "Operation timed out while waiting for an upstream service."
    if isinstance(exc, FileNotFoundError):
        return "Required file or dependency was not available."
    if isinstance(exc, PermissionError):
        return "Permission denied while accessing a required resource."

    message = sanitize_text(str(exc), max_length=max_length)
    return message or fallback
