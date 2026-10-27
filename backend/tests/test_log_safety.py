from subprocess import TimeoutExpired

from app.core.log_safety import safe_exception_message, safe_url_for_log, sanitize_text


def test_safe_url_for_log_strips_query_and_credentials():
    url = "https://user:pass@example.com/path/video.mp4?token=abc123&sig=secret"
    assert safe_url_for_log(url) == "https://example.com/path/video.mp4"


def test_sanitize_text_redacts_common_secret_patterns():
    raw = "Authorization: Bearer abc123 token=xyz api_key=secret-value"
    assert (
        sanitize_text(raw) == "Authorization: Bearer [redacted] token=[redacted] api_key=[redacted]"
    )


def test_safe_exception_message_returns_timeout_fallback():
    exc = TimeoutExpired("ffprobe", 30)
    assert (
        safe_exception_message(exc) == "Operation timed out while waiting for an upstream service."
    )


def test_safe_exception_message_redacts_sensitive_values():
    exc = RuntimeError("Download failed for https://example.com/watch?v=1 token=abc123")
    assert (
        safe_exception_message(exc)
        == "Download failed for https://example.com/watch token=[redacted]"
    )
