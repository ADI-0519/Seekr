from datetime import datetime, timezone

import pytest
from app.models.video import ProcessingStatus
from app.schemas.video import (
    LinkSubmitRequest,
    QuestionRequest,
    SearchRequest,
    VideoResponse,
    VideoUploadRequest,
)
from pydantic import HttpUrl, ValidationError


class TestVideoUploadRequest:
    def test_valid_with_url(self):
        req = VideoUploadRequest(
            title="Test", youtube_url=HttpUrl("https://youtube.com/watch?v=abc")
        )
        assert req.title == "Test"

    def test_valid_no_url(self):
        req = VideoUploadRequest(title="Test")
        assert req.youtube_url is None

    def test_bad_url(self):
        with pytest.raises(ValidationError):
            VideoUploadRequest.model_validate({"title": "Test", "youtube_url": "not-a-url"})

    def test_no_title(self):
        with pytest.raises(ValidationError):
            VideoUploadRequest.model_validate({})

    def test_title_too_long(self):
        with pytest.raises(ValidationError):
            VideoUploadRequest(title="x" * 201)

    def test_title_control_chars_stripped(self):
        req = VideoUploadRequest(title="hello\x00world")
        assert "\x00" not in req.title
        assert "hello" in req.title

    def test_title_whitespace_stripped(self):
        req = VideoUploadRequest(title="  My Lecture  ")
        assert req.title == "My Lecture"


class TestLinkSubmitRequest:
    def test_valid_youtube(self):
        req = LinkSubmitRequest(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert req.url

    def test_rejects_non_youtube_domain(self):
        with pytest.raises(ValidationError):
            LinkSubmitRequest(url="https://vimeo.com/watch?v=dQw4w9WgXcQ")

    def test_rejects_redirect_attack(self):
        with pytest.raises(ValidationError):
            LinkSubmitRequest(url="https://evil.com/?to=https://youtube.com/watch?v=dQw4w9WgXcQ")

    def test_accepts_configured_kaltura_host(self):
        req = LinkSubmitRequest(
            url="https://kaf.keats.kcl.ac.uk/browseandembed/index/media-redirect/entryid/1_abc"
        )
        assert req.url.startswith("https://kaf.keats.kcl.ac.uk/")

    def test_title_sanitized(self):
        req = LinkSubmitRequest(url="https://youtu.be/dQw4w9WgXcQ", title="  test\x00  ")
        assert req.title == "test"

    def test_title_too_long(self):
        with pytest.raises(ValidationError):
            LinkSubmitRequest(url="https://youtu.be/dQw4w9WgXcQ", title="x" * 201)

    def test_empty_title_becomes_none(self):
        req = LinkSubmitRequest(url="https://youtu.be/dQw4w9WgXcQ", title="   ")
        assert req.title is None


class TestSearchRequest:
    def test_defaults(self):
        req = SearchRequest(query="what is machine learning")
        assert req.top_k == 5

    def test_custom_k(self):
        req = SearchRequest(query="test", top_k=10)
        assert req.top_k == 10

    def test_empty(self):
        with pytest.raises(ValidationError):
            SearchRequest.model_validate({})

    def test_query_too_long(self):
        with pytest.raises(ValidationError):
            SearchRequest(query="x" * 501)

    def test_query_at_max_length(self):
        req = SearchRequest(query="x" * 500)
        assert len(req.query) == 500

    def test_empty_query_rejected(self):
        with pytest.raises(ValidationError):
            SearchRequest(query="")

    def test_top_k_too_large(self):
        with pytest.raises(ValidationError):
            SearchRequest(query="test", top_k=51)

    def test_top_k_zero_rejected(self):
        with pytest.raises(ValidationError):
            SearchRequest(query="test", top_k=0)

    def test_query_control_chars_stripped(self):
        req = SearchRequest(query="backprop\x00\x01")
        assert "\x00" not in req.query
        assert "backprop" in req.query

    def test_query_newlines_preserved(self):
        # newlines are legitimate in multi-line queries
        req = SearchRequest(query="line one\nline two")
        assert "\n" in req.query


class TestQuestionRequest:
    def test_ok(self):
        req = QuestionRequest(question="What is AI?")
        assert req.question == "What is AI?"

    def test_empty(self):
        with pytest.raises(ValidationError):
            QuestionRequest.model_validate({})

    def test_question_too_long(self):
        with pytest.raises(ValidationError):
            QuestionRequest(question="x" * 1001)

    def test_question_control_chars_stripped(self):
        req = QuestionRequest(question="what is\x00 gradient descent")
        assert "\x00" not in req.question


class TestVideoResponse:
    def test_from_dict(self):
        resp = VideoResponse(
            id=1,
            title="Lecture 1",
            duration=3600.0,
            youtube_url=None,
            status=ProcessingStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
        assert resp.id == 1
        assert resp.status == ProcessingStatus.PENDING
