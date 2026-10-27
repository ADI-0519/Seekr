import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


# Define the sequential stages of the AI processing pipeline
class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    EXTRACTING_AUDIO = "extracting_audio"
    TRANSCRIBING = "transcribing"
    EXTRACTING_SLIDES = "extracting_slides"
    SEGMENTING = "segmenting"
    SUMMARISING = "summarising"
    EMBEDDING = "embedding"
    COMPLETE = "complete"
    FAILED = "failed"


def now_utc():
    return datetime.now(timezone.utc)


# Core entity representing an uploaded lecture and its metadata
class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    youtube_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audio_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    owner_uid: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    last_playback_position: Mapped[float] = mapped_column(Float, default=0.0)

    # Stored as plain string so it works on sqlite too
    status: Mapped[str] = mapped_column(String(50), default=ProcessingStatus.PENDING.value)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, onupdate=now_utc
    )

    # Relational mappings linking the video to its derived components
    sentences: Mapped[list["Sentence"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    transcript_words: Mapped[list["TranscriptWord"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    segments: Mapped[list["Segment"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    slide_frames: Mapped[list["SlideFrame"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    jobs: Mapped[list["ProcessingJob"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )
    chat_messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )


# Store sentence-level transcript blocks with timing data
class Sentence(Base):
    __tablename__ = "sentences"
    __table_args__ = (Index("ix_sentences_video_time", "video_id", "start_time", "end_time"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text)
    start_time: Mapped[float] = mapped_column(Float)
    end_time: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    video: Mapped["Video"] = relationship(back_populates="sentences")


# Define logical chapters or topics identified within the video
class Segment(Base):
    __tablename__ = "segments"
    __table_args__ = (Index("ix_segments_video_time", "video_id", "start_time", "end_time"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_time: Mapped[float] = mapped_column(Float)
    end_time: Mapped[float] = mapped_column(Float)

    video: Mapped["Video"] = relationship(back_populates="segments")


# Store metadata for extracted visual presentation slides
class SlideFrame(Base):
    __tablename__ = "slide_frames"
    __table_args__ = (Index("ix_slide_frames_video_time", "video_id", "start_time", "end_time"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"))
    frame_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_time: Mapped[float] = mapped_column(Float)
    end_time: Mapped[float] = mapped_column(Float)

    video: Mapped["Video"] = relationship(back_populates="slide_frames")


# Track the execution state of background tasks processing the video
class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"))
    task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="queued")
    current_stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    transcription_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    slides_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    video: Mapped["Video"] = relationship(back_populates="jobs")


# Store word-level transcription data for precise playback alignment
class TranscriptWord(Base):
    __tablename__ = "transcript_words"
    __table_args__ = (Index("ix_transcript_words_video_time", "video_id", "start_time"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"))
    word: Mapped[str] = mapped_column(String(100))
    start_time: Mapped[float] = mapped_column(Float)
    end_time: Mapped[float] = mapped_column(Float)
    probability: Mapped[float | None] = mapped_column(Float, nullable=True)

    video: Mapped["Video"] = relationship(back_populates="transcript_words")


# Define enriched textual blocks used for vector embedding and semantic search
class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (Index("ix_chunks_video_time", "video_id", "start_time", "end_time"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text)
    start_time: Mapped[float] = mapped_column(Float)
    end_time: Mapped[float] = mapped_column(Float)

    slide_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    position_category: Mapped[str | None] = mapped_column(String(20), nullable=True)
    section_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    context_template: Mapped[str | None] = mapped_column(Text, nullable=True)

    video: Mapped["Video"] = relationship(back_populates="chunks")


# Persist user interactions with the AI assistant for contextual history
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_messages_video_id", "video_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20))  # 'user' or 'assistant'
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    mode: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 'retrieval' or 'qa'
    citations_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    results_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    video: Mapped["Video"] = relationship(back_populates="chat_messages")
