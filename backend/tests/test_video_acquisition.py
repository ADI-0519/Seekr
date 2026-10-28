import io
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from app.services.video_acquisition import (
    MAX_DURATION,
    SUPPORTED_FORMATS,
    VIDEO_CONTENT_TYPES,
    VideoDownloader,
    VideoDownloadError,
    VideoMetadata,
    VideoValidationError,
    check_file_has_audio,
    extract_kaltura_entry_id,
    extract_youtube_id,
    get_video_duration,
    infer_video_content_type,
    is_kaltura_url,
    is_youtube_url,
    measure_file_size,
    validate_file_extension,
    validate_uploaded_file,
    validate_url,
)


class TestYouTubeUrlValidation:
    def test_standard_watch_url(self):
        assert is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert is_youtube_url("http://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert is_youtube_url("https://youtube.com/watch?v=dQw4w9WgXcQ")

    def test_short_url(self):
        assert is_youtube_url("https://youtu.be/dQw4w9WgXcQ")
        assert is_youtube_url("http://youtu.be/dQw4w9WgXcQ")

    def test_embed_url(self):
        assert is_youtube_url("https://www.youtube.com/embed/dQw4w9WgXcQ")

    def test_invalid_urls(self):
        assert not is_youtube_url("https://vimeo.com/12345")
        assert not is_youtube_url("https://example.com/video")
        assert not is_youtube_url("")
        assert not is_youtube_url(None)  # type: ignore[arg-type]

    def test_extract_video_id(self):
        assert extract_youtube_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
        assert extract_youtube_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
        assert extract_youtube_id("https://vimeo.com/123") is None


class TestValidateUrl:
    def test_valid_youtube_urls(self):
        assert validate_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert validate_url("https://youtu.be/dQw4w9WgXcQ")

    def test_valid_kaltura_urls(self):
        assert validate_url(
            "https://kaf.keats.kcl.ac.uk/browseandembed/index/media-redirect/entryid/1_94h3gplf/showDescription/false"
        )

    def test_missing_protocol(self):
        # we require http/https
        assert not validate_url("youtube.com/watch?v=dQw4w9WgXcQ")

    def test_non_youtube(self):
        assert not validate_url("https://vimeo.com/12345")

    def test_empty_input(self):
        assert not validate_url("")
        assert not validate_url(None)  # type: ignore[arg-type]


class TestKalturaUrlValidation:
    def test_standard_kaltura_embed_url(self):
        url = "https://kaf.keats.kcl.ac.uk/browseandembed/index/media-redirect/entryid/1_94h3gplf/showDescription/false/showTitle/false"
        assert is_kaltura_url(url)

    def test_extract_entry_id(self):
        url = "https://kaf.keats.kcl.ac.uk/browseandembed/index/media-redirect/entryid/1_l31aczhm/showDescription/false"
        assert extract_kaltura_entry_id(url) == "1_l31aczhm"

    def test_kaltura_direct_url(self):
        url = "https://cdnapisec.kaltura.com/p/123/playManifest/entryId/1_abc123/format/url"
        assert is_kaltura_url(url)

    def test_invalid_urls(self):
        assert not is_kaltura_url("https://youtube.com/watch?v=abc")
        assert not is_kaltura_url("https://example.com/video")
        assert not is_kaltura_url("")
        assert not is_kaltura_url(None)  # type: ignore[arg-type]


class TestFileExtensionValidation:
    def test_supported_formats(self):
        for fmt in SUPPORTED_FORMATS:
            assert validate_file_extension(f"video{fmt}")

    def test_case_insensitive(self):
        assert validate_file_extension("video.MP4")
        assert validate_file_extension("video.WebM")

    def test_unsupported_formats(self):
        assert not validate_file_extension("video.gif")
        assert not validate_file_extension("video.txt")
        assert not validate_file_extension("video")

    def test_empty_filename(self):
        assert not validate_file_extension("")
        assert not validate_file_extension(None)  # type: ignore[arg-type]

    def test_infer_video_content_type(self):
        for ext, content_type in VIDEO_CONTENT_TYPES.items():
            assert infer_video_content_type(f"lecture{ext}") == content_type

    def test_measure_file_size(self):
        buffer = io.BytesIO(b"0123456789")
        assert measure_file_size(buffer) == 10
        assert buffer.tell() == 0


class TestFfprobeHelpers:
    @patch("subprocess.run")
    def test_check_has_audio_true(self, mock_run):
        mock_run.return_value = MagicMock(stdout="audio\n", returncode=0)
        assert check_file_has_audio("/tmp/test.mp4") is True

    @patch("subprocess.run")
    def test_check_has_audio_false(self, mock_run):
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        assert check_file_has_audio("/tmp/test.mp4") is False

    @patch("subprocess.run")
    def test_check_audio_ffprobe_timeout(self, mock_run):
        from subprocess import TimeoutExpired

        mock_run.side_effect = TimeoutExpired("ffprobe", 30)
        # should return True (assume audio) when we cant check
        assert check_file_has_audio("/tmp/test.mp4") is True

    @patch("subprocess.run")
    def test_get_duration(self, mock_run):
        mock_run.return_value = MagicMock(stdout="123.45\n", returncode=0)
        assert get_video_duration("/tmp/test.mp4") == 123.45

    @patch("subprocess.run")
    def test_get_duration_failure(self, mock_run):
        mock_run.return_value = MagicMock(stdout="", returncode=1)
        assert get_video_duration("/tmp/test.mp4") is None


class TestValidateUploadedFile:
    def test_file_not_found(self):
        with pytest.raises(VideoValidationError, match="not found"):
            validate_uploaded_file("/nonexistent/path.mp4", "video.mp4")

    def test_unsupported_format(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"hello")
            path = f.name
        try:
            with pytest.raises(VideoValidationError, match="Unsupported format"):
                validate_uploaded_file(path, "document.txt")
        finally:
            os.unlink(path)

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            path = f.name
        try:
            with pytest.raises(VideoValidationError, match="empty"):
                validate_uploaded_file(path, "video.mp4")
        finally:
            os.unlink(path)

    @patch("app.services.video_acquisition.check_file_has_audio")
    @patch("app.services.video_acquisition.get_video_duration")
    def test_no_audio(self, mock_duration, mock_audio):
        mock_audio.return_value = False
        mock_duration.return_value = 60.0

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"x" * 1000)
            path = f.name
        try:
            with pytest.raises(VideoValidationError, match="no audio"):
                validate_uploaded_file(path, "video.mp4")
        finally:
            os.unlink(path)

    @patch("app.services.video_acquisition.check_file_has_audio")
    @patch("app.services.video_acquisition.get_video_duration")
    def test_video_too_long(self, mock_duration, mock_audio):
        mock_audio.return_value = True
        mock_duration.return_value = MAX_DURATION + 1

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"x" * 1000)
            path = f.name
        try:
            with pytest.raises(VideoValidationError, match="too long"):
                validate_uploaded_file(path, "video.mp4")
        finally:
            os.unlink(path)

    @patch("app.services.video_acquisition.check_file_has_audio")
    @patch("app.services.video_acquisition.get_video_duration")
    def test_valid_file(self, mock_duration, mock_audio):
        mock_audio.return_value = True
        mock_duration.return_value = 300.0

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"x" * 1000)
            path = f.name
        try:
            meta = validate_uploaded_file(path, "lecture.mp4")
            assert isinstance(meta, VideoMetadata)
            assert meta.title == "lecture"
            assert meta.duration == 300.0
            assert meta.has_audio is True
        finally:
            os.unlink(path)


class TestVideoDownloader:
    @patch("yt_dlp.YoutubeDL")
    def test_extract_metadata(self, mock_ydl_class):
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.return_value = {
            "title": "Test Video",
            "duration": 600,
        }
        mock_ydl_class.return_value = mock_ydl

        dl = VideoDownloader()
        info = dl.extract_metadata("https://youtube.com/watch?v=abc123")

        assert info["title"] == "Test Video"
        assert info["duration"] == 600

    @patch("yt_dlp.YoutubeDL")
    def test_extract_metadata_private_video(self, mock_ydl_class):
        import yt_dlp

        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.side_effect = yt_dlp.DownloadError("Video is private")
        mock_ydl_class.return_value = mock_ydl

        dl = VideoDownloader()
        with pytest.raises(VideoDownloadError, match="not accessible"):
            dl.extract_metadata("https://youtube.com/watch?v=private123")

    @patch.object(VideoDownloader, "extract_metadata")
    def test_download_video_too_long(self, mock_extract):
        mock_extract.return_value = {
            "title": "Super Long Lecture",
            "duration": MAX_DURATION + 1000,
        }

        dl = VideoDownloader()
        with pytest.raises(VideoValidationError, match="too long"):
            dl.download("https://youtube.com/watch?v=toolong")

    def test_cleanup_removes_temp_dir(self):
        dl = VideoDownloader()
        temp_dir = dl.download_dir
        assert os.path.exists(temp_dir)

        dl.cleanup()
        assert not os.path.exists(temp_dir)

    def test_cleanup_handles_missing_dir(self):
        dl = VideoDownloader()
        dl.download_dir = "/nonexistent/path/that/doesnt/exist"
        # should not raise
        dl.cleanup()

    @patch("yt_dlp.YoutubeDL")
    def test_auth_error_for_kaltura_url(self, mock_ydl_class):
        import yt_dlp

        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.side_effect = yt_dlp.DownloadError("HTTP Error 403: Forbidden")
        mock_ydl_class.return_value = mock_ydl

        dl = VideoDownloader()
        with pytest.raises(VideoDownloadError, match="Authentication required"):
            dl.extract_metadata(
                "https://kaf.keats.kcl.ac.uk/browseandembed/index/media-redirect/entryid/1_abc/showDescription/false"
            )

    @patch("yt_dlp.YoutubeDL")
    def test_extract_metadata_does_not_leak_sensitive_query_values(self, mock_ydl_class):
        import yt_dlp

        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.side_effect = yt_dlp.DownloadError(
            "Download failed for https://example.com/watch?v=1&token=super-secret"
        )
        mock_ydl_class.return_value = mock_ydl

        dl = VideoDownloader()
        with pytest.raises(
            VideoDownloadError, match="Download failed while fetching video metadata."
        ):
            dl.extract_metadata("https://youtube.com/watch?v=abc123")


class TestEdgeCases:
    def test_unicode_filename(self):
        assert validate_file_extension("ビデオ.mp4")
        assert validate_file_extension("講義_第1回.webm")

    def test_special_chars_in_filename(self):
        assert validate_file_extension("video (1).mp4")
        assert validate_file_extension("lecture - intro.mp4")

    def test_youtube_url_with_extra_params(self):
        # these should still work since video id is captured
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLtest&t=120"
        # our regex only checks the base pattern, extra params dont matter as long as the v= param is there
        assert is_youtube_url(url) or extract_youtube_id(url) == "dQw4w9WgXcQ"

    def test_youtube_url_without_www(self):
        assert is_youtube_url("https://youtube.com/watch?v=dQw4w9WgXcQ")
