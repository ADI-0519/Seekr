import re
import unicodedata
from datetime import datetime
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

# Define allowed domains for video link submission
_ALLOWED_VIDEO_DOMAINS = {
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
    "www.youtu.be",
    "kaf.keats.kcl.ac.uk",
}


# Remove hidden control characters from text inputs to prevent formatting issues
def strip_control_chars(v: str) -> str:
    return "".join(c for c in v if unicodedata.category(c) != "Cc" or c in "\n\t")


# Schema for direct file uploads or initial video creation
class VideoUploadRequest(BaseModel):
    title: str = Field(..., max_length=200)
    youtube_url: HttpUrl | None = None

    @field_validator("title", mode="before")
    @classmethod
    def sanitize_title(cls, v: str) -> str:
        return strip_control_chars(str(v).strip())


# Schema for submitting external video links for processing
class LinkSubmitRequest(BaseModel):
    url: str
    title: str | None = Field(default=None, max_length=200)

    @field_validator("title", mode="before")
    @classmethod
    def sanitize_title(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return strip_control_chars(str(v).strip()) or None

    @field_validator("url")
    @classmethod
    def validate_video_url(cls, v: str) -> str:
        v = v.strip()
        youtube_patterns = [
            r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
            r"(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})",
            r"(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})",
        ]
        kaltura_patterns = [
            r"https?://kaf\.keats\.kcl\.ac\.uk/browseandembed/index/media-redirect/entryid/([a-zA-Z0-9_]+)",
            r"https?://[\w.-]*kaltura\.com/.+/entryId/([a-zA-Z0-9_]+)",
        ]
        if not any(re.search(p, v) for p in youtube_patterns + kaltura_patterns):
            raise ValueError("Unsupported URL. Paste a YouTube or Kaltura link.")

        # re.search matches anywhere in the string
        parsed = urlparse(v if "://" in v else f"https://{v}")
        host = parsed.netloc.lower()
        if host not in _ALLOWED_VIDEO_DOMAINS and not host.endswith(".kaltura.com"):
            raise ValueError("Unsupported URL. Paste a YouTube or Kaltura link.")
        return v


# Alias for backwards compatibility or specific YouTube endpoint routing
YouTubeSubmitRequest = LinkSubmitRequest


# Schema for requesting keyword or semantic search across video content
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=50)

    @field_validator("query", mode="before")
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        return strip_control_chars(str(v))


# Schema for asking direct questions to the AI assistant
class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)

    @field_validator("question", mode="before")
    @classmethod
    def sanitize_question(cls, v: str) -> str:
        return strip_control_chars(str(v))


# Output schema for core video metadata and playback state
class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    duration: float | None = None
    youtube_url: str | None = None
    storage_path: str | None = None
    thumbnail_path: str | None = None
    overview: str | None = None
    status: str
    created_at: datetime
    from_cache: bool = False
    video_url: str | None = None
    thumbnail_url: str | None = None
    last_playback_position: float = 0.0


# Output schema for tracking specific pipeline stages during processing
class VideoStatusResponse(BaseModel):
    id: int
    status: str
    current_stage: str | None = None
    transcription_stage: str | None = None
    slides_stage: str | None = None
    error_message: str | None = None


# Schema for syncing the user playback position to the backend
class PlaybackPositionRequest(BaseModel):
    position_seconds: float = Field(..., ge=0.0)


# Output schema confirming the updated playback position
class PlaybackPositionResponse(BaseModel):
    video_id: int
    position_seconds: float


# Output schema for a single line of transcribed text
class SentenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    start_time: float
    end_time: float


# Output schema for a logically grouped topic or chapter
class SegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    summary: str | None = None
    start_time: float
    end_time: float


# Output schema for an extracted presentation slide
class SlideFrameResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    start_time: float
    end_time: float
    ocr_text: str | None = None
    frame_url: str | None = None


# Output schema for the complete collection of slides for a video
class SlideListResponse(BaseModel):
    video_id: int
    total: int
    slides: list[SlideFrameResponse]


# Output schema for the full video transcript and structural segments
class TranscriptResponse(BaseModel):
    video_id: int
    sentences: list[SentenceResponse]
    segments: list[SegmentResponse]


# Output schema for an individual search match
class SearchResult(BaseModel):
    text: str
    start_time: float
    end_time: float
    score: float
    segment_title: str | None = None


# Output schema returning multiple search matches for a query
class SearchResponse(BaseModel):
    results: list[SearchResult]
    query: str


# Output schema for a specific reference used by the AI to answer a question
class Citation(BaseModel):
    start_time: float
    end_time: float
    text: str
    segment_title: str | None = None


# Output schema for an AI generated answer with supporting citations
class AnswerResponse(BaseModel):
    question: str
    answer: str
    citations: list[Citation]


# Schema for a unified chat query that handles both search and Q&A modes
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    mode: Literal["auto", "retrieval", "qa"] = "auto"
    top_k: int = Field(default=5, ge=1, le=50)

    @field_validator("query", mode="before")
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        return strip_control_chars(str(v))


# Output schema for the unified chat query response
class QueryResponse(BaseModel):
    query: str
    mode: Literal["retrieval", "qa"]
    results: list[SearchResult] | None = None
    answer: str | None = None
    citations: list[Citation] | None = None


# Schema for recording a new message in the chat history
class ChatMessageCreate(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    text: str | None = None
    mode: str | None = None
    citations_json: str | None = None
    results_json: str | None = None


# Output schema for retrieving a single message from chat history
class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    text: str | None = None
    mode: str | None = None
    citations_json: str | None = None
    results_json: str | None = None
    created_at: datetime


# Schema for submitting a batch update to the chat history
class ChatHistoryRequest(BaseModel):
    messages: list[ChatMessageCreate]


# Output schema for a single AI generated study note
class GeneratedNoteItem(BaseModel):
    segment_id: int
    title: str
    notes_markdown: str
    start_time: float
    end_time: float


# Output schema for the complete list of study notes for a video
class NotesListResponse(BaseModel):
    video_id: int
    notes: list[GeneratedNoteItem]


# Schema for requesting a PDF export of generated notes
class NotesExportRequest(BaseModel):
    notes: list[GeneratedNoteItem]
