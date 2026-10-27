import logging
import os
import tempfile
import time
from datetime import datetime, timezone

from celery import chord, shared_task
from celery.signals import worker_ready
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.exc import ObjectDeletedError

from app.core.config import get_settings
from app.core.log_safety import safe_exception_message, safe_url_for_log
from app.models.video import ProcessingJob, ProcessingStatus, Video
from app.services.storage import StorageService
from app.services.video_acquisition import (
    VideoValidationError,
    YouTubeDownloader,
    YouTubeDownloadError,
)

log = logging.getLogger(__name__)

_settings = get_settings()
_sync_url = _settings.database_url.replace("+asyncpg", "")
_sync_engine = create_engine(_sync_url, pool_pre_ping=True)
SyncSession = sessionmaker(bind=_sync_engine)
embedder_singleton = None


@worker_ready.connect
def preload_models(**kwargs):  # load models into GPU memory at startup so first task doesn't stall
    sender = kwargs.get("sender")
    queues = {q.name for q in sender.task_consumer.queues} if sender else set()
    settings = get_settings()

    if not queues or "transcription" in queues:
        try:
            from app.services.transcription import get_transcription_service

            svc = get_transcription_service(
                model_name=settings.whisper_model, device=settings.whisper_device
            )
            svc.warmup()
            import struct
            import tempfile
            import wave

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                dummy_path = f.name
            with wave.open(dummy_path, "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(struct.pack("<" + "h" * 160, *([0] * 160)))
            try:
                svc.transcribe(dummy_path)
            except Exception:
                pass
            finally:
                import os as _os

                _os.unlink(dummy_path)
            log.info("whisper model preloaded")
        except Exception:
            log.warning("whisper preload failed, will load on first task", exc_info=True)

    if not queues or "default" in queues:
        try:
            from app.services.embedding import EmbeddingService

            global embedder_singleton
            embedder_singleton = EmbeddingService()
            embedder_singleton.embed_texts(["warmup"])
            log.info("embedding model preloaded")
        except Exception:
            log.warning("embedding preload failed, will load on first task", exc_info=True)

    if not queues or "retrieval" in queues:
        try:
            from app.services.reranker import RerankingService

            reranker_svc = RerankingService()
            reranker_svc.rerank("warmup", [{"text": "warmup", "slide_text": ""}], top_k=1)
            log.info("reranker model preloaded")
        except Exception:
            log.warning("reranker preload failed, will load on first task", exc_info=True)

    if not queues or "slides" in queues:
        try:
            import easyocr

            reader = easyocr.Reader(["en"], gpu=True)
            import numpy as np

            reader.readtext(np.zeros((64, 64, 3), dtype=np.uint8))
            log.info("easyocr model preloaded")
        except Exception:
            log.warning("easyocr preload failed, will load on first task", exc_info=True)


# pipeline stages: (status, progress %, simulated duration in seconds)
PIPELINE_STAGES = [
    (ProcessingStatus.EXTRACTING_AUDIO, 10, 1.0),
    (ProcessingStatus.TRANSCRIBING, 30, 2.0),
    (ProcessingStatus.EXTRACTING_SLIDES, 50, 1.0),
    (ProcessingStatus.SEGMENTING, 65, 1.0),
    (ProcessingStatus.EMBEDDING, 80, 1.5),
]


def update_job(session: Session, job_id: int, **fields):
    job = session.get(ProcessingJob, job_id)
    if job:
        for k, v in fields.items():
            setattr(job, k, v)
        session.commit()
    return job


def get_embedder():
    global embedder_singleton
    if embedder_singleton is None:
        from app.services.embedding import EmbeddingService

        embedder_singleton = EmbeddingService()

    return embedder_singleton


def get_or_create_job(session: Session, video_id: int, task_id: str | None) -> ProcessingJob:
    stmt = (
        select(ProcessingJob)
        .where(ProcessingJob.video_id == video_id)
        .order_by(ProcessingJob.created_at.desc())
    )
    existing = session.execute(stmt).scalars().first()
    if existing and existing.task_id == task_id and existing.status == "queued":
        existing.status = "running"
        existing.current_stage = ProcessingStatus.EXTRACTING_AUDIO.value
        existing.started_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(existing)
        return existing

    job = ProcessingJob(
        video_id=video_id,
        task_id=task_id,
        status="running",
        current_stage=ProcessingStatus.EXTRACTING_AUDIO.value,
        started_at=datetime.now(timezone.utc),
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def find_job(session: Session, video_id: int) -> ProcessingJob | None:
    stmt = (
        select(ProcessingJob)
        .where(ProcessingJob.video_id == video_id)
        .order_by(ProcessingJob.created_at.desc())
    )
    return session.execute(stmt).scalars().first()


def resolve_job_id(session: Session, video_id: int) -> int | None:
    try:
        job = find_job(session, video_id)
        return int(job.id) if job and job.id is not None else None
    except ObjectDeletedError:
        return None


def is_cancelled_or_deleted(session: Session, video_id: int) -> bool:
    video = session.get(Video, video_id)
    if video is None:
        return True
    job = find_job(session, video_id)
    return bool(job and job.status == "cancelled")


def lock_video_for_write(session: Session, video_id: int) -> Video | None:
    stmt = select(Video).where(Video.id == video_id).with_for_update()
    return session.execute(stmt).scalars().first()


def update_video_status(
    session: Session, video_id: int, status: ProcessingStatus, error: str | None = None
):
    video = session.get(Video, video_id)
    if video:
        video.status = status.value
        video.error_message = error
        session.commit()


def handle_youtube_download(session: Session, video: Video) -> None:
    if not video.youtube_url:
        raise ValueError("No youtube_url on video")

    downloader = YouTubeDownloader()

    try:
        log.info("downloading youtube video %s: %s", video.id, safe_url_for_log(video.youtube_url))
        metadata = downloader.download(video.youtube_url)

        storage = StorageService()
        storage.ensure_bucket_exists()
        key = storage.generate_object_key(video.id, f"video{metadata.format}")

        if not metadata.local_path:
            raise YouTubeDownloadError("Download succeeded but no local path")

        with open(metadata.local_path, "rb") as f:
            storage.upload_fileobj(f, key, content_type="video/mp4")

        video.storage_path = key
        video.duration = metadata.duration
        _bad_titles = {"YouTube Video", "Imported Video", "Private Video", "Video Unavailable", ""}
        if metadata.title and video.title in _bad_titles:
            video.title = metadata.title
        session.commit()

        log.info("youtube download complete for video %s: %s", video.id, key)

    finally:
        downloader.cleanup()


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def process_video(self, video_id: int):
    session = SyncSession()
    job = None

    try:
        video = session.get(Video, video_id)
        if not video:
            raise ValueError(f"Video {video_id} not found")

        # handle youtube download if needed
        if video.youtube_url and not video.storage_path:
            try:
                handle_youtube_download(session, video)
            except (VideoValidationError, YouTubeDownloadError) as e:
                safe_message = safe_exception_message(e, fallback="Video download failed.")
                log.error(
                    "youtube download failed for video %s: %s: %s",
                    video_id,
                    type(e).__name__,
                    safe_message,
                )
                update_video_status(session, video_id, ProcessingStatus.FAILED, safe_message)
                raise

        job = get_or_create_job(session, video_id, self.request.id)

        log.info("job %s started for video %s (celery_id=%s)", job.id, video_id, self.request.id)
        update_job(
            session, job.id, current_stage=ProcessingStatus.EXTRACTING_AUDIO.value, status="running"
        )
        update_video_status(session, video_id, ProcessingStatus.EXTRACTING_AUDIO)
        run_audio_extraction(session, video_id)

        # fan out transcription and slides in parallel, then finish pipeline
        update_job(
            session,
            job.id,
            current_stage="parallel_processing",
            transcription_stage="queued",
            slides_stage="queued",
        )
        update_video_status(session, video_id, ProcessingStatus.TRANSCRIBING)

        chord(
            [transcribe_audio.s(video_id), extract_slides.s(video_id)],
            finish_pipeline.si(video_id),
        ).apply_async()

        log.info("job %s dispatched parallel branches for video %s", job.id, video_id)
        return {"job_id": job.id, "status": "running", "stage": "parallel_dispatched"}

    except Exception as exc:
        safe_message = safe_exception_message(exc, fallback="Video processing failed.")
        log.error("job failed for video %s: %s: %s", video_id, type(exc).__name__, safe_message)
        session.rollback()

        if job and job.id:
            try:
                update_job(
                    session,
                    job.id,
                    status="failed",
                    error_message=safe_message,
                    completed_at=datetime.now(timezone.utc),
                )
            except Exception as update_exc:
                log.error(
                    "couldnt mark job %s as failed: %s: %s",
                    job.id,
                    type(update_exc).__name__,
                    safe_exception_message(update_exc),
                )

        try:
            update_video_status(session, video_id, ProcessingStatus.FAILED, safe_message)
        except Exception as update_exc:
            log.error(
                "couldnt mark video %s as failed: %s: %s",
                video_id,
                type(update_exc).__name__,
                safe_exception_message(update_exc),
            )

        if isinstance(exc, (VideoValidationError, YouTubeDownloadError)):
            raise

        raise self.retry(exc=exc, countdown=60)

    finally:
        session.close()


@shared_task(bind=True, max_retries=1, default_retry_delay=30)
def transcribe_audio(self, video_id: int):
    log.info("transcribe_audio starting for video %s", video_id)
    session = SyncSession()
    try:
        if is_cancelled_or_deleted(session, video_id):
            log.info("transcribe_audio skipped for cancelled/deleted video %s", video_id)
            return {"branch": "transcription", "status": "cancelled"}

        job_id = resolve_job_id(session, video_id)
        if job_id:
            update_job(session, job_id, transcription_stage="running")

        run_transcription(session, video_id)

        if is_cancelled_or_deleted(session, video_id):
            log.info("transcribe_audio completed but video %s was cancelled/deleted", video_id)
            return {"branch": "transcription", "status": "cancelled"}

        if job_id:
            update_job(session, job_id, transcription_stage="done")
        log.info("transcribe_audio complete for video %s", video_id)
        return {"branch": "transcription", "status": "done"}

    except Exception as exc:
        log.error(
            "transcribe_audio failed for video %s: %s: %s",
            video_id,
            type(exc).__name__,
            safe_exception_message(exc),
        )
        session.rollback()
        if is_cancelled_or_deleted(session, video_id):
            log.info("transcribe_audio aborting retries for cancelled/deleted video %s", video_id)
            return {"branch": "transcription", "status": "cancelled"}
        if isinstance(exc, IntegrityError) and not session.get(Video, video_id):
            log.info("transcribe_audio foreign-key write skipped for deleted video %s", video_id)
            return {"branch": "transcription", "status": "cancelled"}
        job_id = resolve_job_id(session, video_id)
        if job_id:
            try:
                update_job(session, job_id, transcription_stage="failed")
            except Exception:
                pass
        raise self.retry(exc=exc, countdown=30)
    finally:
        session.close()


@shared_task(bind=True, max_retries=1, default_retry_delay=30)
def extract_slides(self, video_id: int):
    log.info("extract_slides starting for video %s", video_id)
    session = SyncSession()
    try:
        if is_cancelled_or_deleted(session, video_id):
            log.info("extract_slides skipped for cancelled/deleted video %s", video_id)
            return {"branch": "slides", "status": "cancelled", "frame_count": 0}

        job = find_job(session, video_id)
        job_id = resolve_job_id(session, video_id)
        if job and job.slides_stage == "done":
            log.info("extract_slides already done for video %s, skipping", video_id)
            from app.models.video import SlideFrame

            count = (
                session.execute(
                    select(func.count())
                    .select_from(SlideFrame)
                    .where(SlideFrame.video_id == video_id)
                ).scalar()
                or 0
            )
            return {"branch": "slides", "status": "done", "frame_count": count}

        if job_id:
            update_job(session, job_id, slides_stage="running")

        count = run_slide_extraction(session, video_id)

        if is_cancelled_or_deleted(session, video_id):
            log.info("extract_slides completed but video %s was cancelled/deleted", video_id)
            return {"branch": "slides", "status": "cancelled", "frame_count": 0}

        if job_id:
            update_job(session, job_id, slides_stage="done")
        log.info("extract_slides complete for video %s: %d frames", video_id, count)
        return {"branch": "slides", "status": "done", "frame_count": count}

    except Exception as exc:
        log.error(
            "extract_slides failed for video %s: %s: %s",
            video_id,
            type(exc).__name__,
            safe_exception_message(exc),
        )
        session.rollback()
        if is_cancelled_or_deleted(session, video_id):
            log.info("extract_slides aborting retries for cancelled/deleted video %s", video_id)
            return {"branch": "slides", "status": "cancelled", "frame_count": 0}
        if isinstance(exc, IntegrityError) and not session.get(Video, video_id):
            log.info("extract_slides foreign-key write skipped for deleted video %s", video_id)
            return {"branch": "slides", "status": "cancelled", "frame_count": 0}
        job_id = resolve_job_id(session, video_id)
        if job_id:
            try:
                update_job(session, job_id, slides_stage="failed")
            except Exception:
                pass
        raise self.retry(exc=exc, countdown=30)
    finally:
        session.close()


@shared_task(bind=True, max_retries=1, default_retry_delay=30)
def finish_pipeline(self, video_id: int):
    log.info("finish_pipeline starting for video %s", video_id)
    session = SyncSession()
    try:
        if is_cancelled_or_deleted(session, video_id):
            log.info("finish_pipeline skipped for cancelled/deleted video %s", video_id)
            return {"job_id": None, "status": "cancelled"}

        job = find_job(session, video_id)
        if job and job.current_stage == ProcessingStatus.COMPLETE.value:
            log.info("finish_pipeline already complete for video %s, skipping", video_id)
            return {"job_id": job.id, "status": "done"}

        # segmenting
        if job:
            update_job(session, job.id, current_stage=ProcessingStatus.SEGMENTING.value)
        update_video_status(session, video_id, ProcessingStatus.SEGMENTING)
        run_segmentation(session, video_id)

        # summary generation
        if job:
            update_job(session, job.id, current_stage=ProcessingStatus.SUMMARISING.value)
        update_video_status(session, video_id, ProcessingStatus.SUMMARISING)
        run_summary_generation(session, video_id)

        # embedding
        if job:
            update_job(session, job.id, current_stage=ProcessingStatus.EMBEDDING.value)
        update_video_status(session, video_id, ProcessingStatus.EMBEDDING)
        run_embedding(session, video_id)

        if job:
            update_job(
                session,
                job.id,
                status="done",
                current_stage=ProcessingStatus.COMPLETE.value,
                completed_at=datetime.now(timezone.utc),
            )
        update_video_status(session, video_id, ProcessingStatus.COMPLETE)
        log.info("finish_pipeline complete for video %s", video_id)
        return {"job_id": job.id if job else None, "status": "done"}

    except Exception as exc:
        safe_message = safe_exception_message(
            exc, fallback="Finishing the lecture pipeline failed."
        )
        log.error(
            "finish_pipeline failed for video %s: %s: %s",
            video_id,
            type(exc).__name__,
            safe_message,
        )
        session.rollback()
        job = find_job(session, video_id)
        if job:
            try:
                update_job(
                    session,
                    job.id,
                    status="failed",
                    error_message=safe_message,
                    completed_at=datetime.now(timezone.utc),
                )
            except Exception:
                pass
        update_video_status(session, video_id, ProcessingStatus.FAILED, safe_message)
        raise self.retry(exc=exc, countdown=30)
    finally:
        session.close()


def run_segmentation(session: Session, video_id: int) -> int:
    from app.models.video import Segment, Sentence, SlideFrame
    from app.services.segmentation import TopicSegmenter
    from app.services.sentence_reconstruction import ReconstructedSentence

    video = session.get(Video, video_id)
    if not video:
        raise ValueError(f"Video {video_id} not found")

    stmt = select(Sentence).where(Sentence.video_id == video_id).order_by(Sentence.start_time)
    sentence_rows = session.execute(stmt).scalars().all()

    if not sentence_rows:
        raise ValueError(f"Video {video_id} has no sentences - run transcription first")

    reconstructed = [
        ReconstructedSentence(
            text=s.text,
            start_time=s.start_time,
            end_time=s.end_time,
            word_start_idx=0,
            word_end_idx=0,
        )
        for s in sentence_rows
    ]

    # grab slide frames so the segmenter can use OCR for boundaries and title hints
    frame_rows = (
        session.execute(
            select(SlideFrame)
            .where(SlideFrame.video_id == video_id)
            .order_by(SlideFrame.start_time)
        )
        .scalars()
        .all()
    )
    slide_frames = (
        [
            {"ocr_text": f.ocr_text, "start_time": f.start_time, "end_time": f.end_time}
            for f in frame_rows
        ]
        if frame_rows
        else None
    )

    session.query(Segment).filter(Segment.video_id == video_id).delete(synchronize_session=False)

    segmenter = TopicSegmenter()
    results = segmenter.segment(reconstructed, video_title=video.title, slide_frames=slide_frames)

    for seg in results:
        session.add(
            Segment(
                video_id=video_id,
                title=seg.title,
                start_time=seg.start_time,
                end_time=seg.end_time,
            )
        )

    session.commit()
    log.info(
        "segmentation complete for video %s: %d segments",
        video_id,
        len(results),
    )
    return len(results)


def run_summary_generation(session: Session, video_id: int) -> int:
    from app.models.video import Segment, Sentence, SlideFrame
    from app.services.summary_generation import SummaryGenerator, SummaryInput

    video = session.get(Video, video_id)
    if not video:
        raise ValueError(f"Video {video_id} not found")

    stmt = select(Segment).where(Segment.video_id == video_id).order_by(Segment.start_time)
    segments = session.execute(stmt).scalars().all()

    if not segments:
        log.warning("No segments found for video %s — skipping summary generation", video_id)
        return 0

    all_sentences = (
        session.execute(
            select(Sentence).where(Sentence.video_id == video_id).order_by(Sentence.start_time)
        )
        .scalars()
        .all()
    )

    all_frames = (
        session.execute(
            select(SlideFrame)
            .where(SlideFrame.video_id == video_id)
            .order_by(SlideFrame.start_time)
        )
        .scalars()
        .all()
    )

    from app.services.summary_generation import ADJACENT_EXCERPT_WORDS

    titles = [seg.title for seg in segments]

    seg_texts = []
    for seg in segments:
        seg_texts.append(
            " ".join(
                s.text
                for s in all_sentences
                if s.start_time >= seg.start_time and s.end_time <= seg.end_time
            )
        )

    def excerpt_tail(text: str) -> str:
        words = text.split()
        return " ".join(words[-ADJACENT_EXCERPT_WORDS:])

    def excerpt_head(text: str) -> str:
        words = text.split()
        return " ".join(words[:ADJACENT_EXCERPT_WORDS])

    inputs: list[SummaryInput] = []
    for i, seg in enumerate(segments):
        # deduplicate OCR lines from slides that overlap this segment
        seen: set[str] = set()
        slide_lines: list[str] = []
        for frame in all_frames:
            if frame.start_time >= seg.end_time or frame.end_time <= seg.start_time:
                continue
            for line in (frame.ocr_text or "").split("\n"):
                key = line.strip().lower()
                if key and key not in seen:
                    seen.add(key)
                    slide_lines.append(line.strip())

        inputs.append(
            SummaryInput(
                segment_id=seg.id,
                title=seg.title,
                transcript_text=seg_texts[i],
                start_time=seg.start_time,
                end_time=seg.end_time,
                slide_text="\n".join(slide_lines),
                prev_title=titles[i - 1] if i > 0 else "",
                next_title=titles[i + 1] if i < len(titles) - 1 else "",
                prev_excerpt=excerpt_tail(seg_texts[i - 1]) if i > 0 else "",
                next_excerpt=excerpt_head(seg_texts[i + 1]) if i < len(titles) - 1 else "",
            )
        )

    generator = SummaryGenerator()
    results = generator.generate_all(inputs)

    for result in results:
        seg_row = session.get(Segment, result.segment_id)
        if seg_row:
            seg_row.summary = result.summary

    # same order as inputs since generate_all preserves it
    overview_pairs = [(inp.title, res.summary) for inp, res in zip(inputs, results)]
    try:
        video.overview = generator.generate_overview(overview_pairs)
    except Exception:
        log.warning("overview generation failed for video %s, skipping", video_id)

    session.commit()
    log.info(
        "summary generation complete for video %s: %d segments summarised",
        video_id,
        len(results),
    )
    return len(results)


def run_audio_extraction(session: Session, video_id: int) -> str:
    from app.services.audio import AudioExtractor
    from app.services.storage import StorageService

    video = session.get(Video, video_id)
    if not video or not video.storage_path:
        raise ValueError(f"Video {video_id} has no storage_path")
    storage = StorageService()
    extractor = AudioExtractor()

    ext = os.path.splitext(video.storage_path)[1] or ".mp4"
    tmp_video = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    try:
        storage.download_to_fileobj(video.storage_path, tmp_video)
        tmp_video.close()

        wav_path = extractor.extract(tmp_video.name)
        try:
            source_duration = extractor.probe_video_duration(tmp_video.name)
            extractor.validate_output(wav_path, expected_duration=source_duration)

            audio_key = storage.generate_audio_key(video_id)
            with open(wav_path, "rb") as f:
                storage.upload_fileobj(f, audio_key, content_type="audio/wav")

            latest_video = session.get(Video, video_id)
            if latest_video is None:
                log.info(
                    "audio extraction finished but video %s was deleted/cancelled; skipping DB write",
                    video_id,
                )
                return audio_key

            latest_video.audio_path = audio_key
            latest_video.duration = source_duration
            session.commit()
            log.info("Audio extracted for video %s -> %s", video_id, audio_key)
        finally:
            extractor.cleanup(wav_path)

        try:
            jpg_path = extractor.extract_thumbnail(tmp_video.name)
            try:
                thumb_key = storage.generate_thumbnail_key(video_id)
                with open(jpg_path, "rb") as f:
                    storage.upload_fileobj(f, thumb_key, content_type="image/jpeg")
                latest_video = session.get(Video, video_id)
                if latest_video is None:
                    log.info(
                        "thumbnail extraction finished but video %s was deleted/cancelled; skipping DB write",
                        video_id,
                    )
                    return audio_key

                latest_video.thumbnail_path = thumb_key
                session.commit()
                log.info("Thumbnail extracted for video %s -> %s", video_id, thumb_key)
            finally:
                extractor.cleanup(jpg_path)
        except Exception:
            log.warning("Thumbnail extraction failed for video %s", video_id, exc_info=True)
        return audio_key
    finally:
        extractor.cleanup(tmp_video.name)


def run_transcription(session: Session, video_id: int) -> None:
    from app.models.video import Sentence, TranscriptWord
    from app.services.sentence_reconstruction import SentenceReconstructor

    video = session.get(Video, video_id)
    if not video or not video.audio_path:
        raise ValueError(f"Video {video_id} has no audio_path - run audio extraction first")

    settings = get_settings()
    storage = StorageService()

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    try:
        from app.services.transcription import get_transcription_service

        storage.download_to_fileobj(video.audio_path, tmp)
        tmp.close()

        service = get_transcription_service(
            model_name=settings.whisper_model, device=settings.whisper_device
        )
        words, segment_ranges = service.transcribe_with_segments(tmp.name)
        reconstructor = SentenceReconstructor(
            pause_threshold_secs=settings.sentence_pause_threshold_secs,
            max_words_per_sentence=settings.sentence_max_words,
            max_sentence_duration_secs=settings.sentence_max_duration_secs,
            segment_hint_tolerance_secs=settings.sentence_segment_hint_tolerance_secs,
        )
        sentences = reconstructor.reconstruct_sentences(words, segment_ranges=segment_ranges)

        locked_video = lock_video_for_write(session, video_id)
        if locked_video is None or is_cancelled_or_deleted(session, video_id):
            log.info(
                "transcription finished but video %s was deleted/cancelled; skipping DB write",
                video_id,
            )
            return

        session.query(TranscriptWord).filter(TranscriptWord.video_id == video_id).delete(
            synchronize_session=False
        )
        session.query(Sentence).filter(Sentence.video_id == video_id).delete(
            synchronize_session=False
        )

        word_rows = []
        for w in words:
            prob = w.get("probability")
            probability = None if prob is None else float(prob)

            word_rows.append(
                TranscriptWord(
                    video_id=video_id,
                    word=w["word"],
                    start_time=float(w["start"]),
                    end_time=float(w["end"]),
                    probability=probability,
                )
            )
        sentence_rows = [
            Sentence(
                video_id=video_id,
                text=s.text,
                start_time=s.start_time,
                end_time=s.end_time,
                confidence=None,
            )
            for s in sentences
        ]

        session.add_all(word_rows)
        session.add_all(sentence_rows)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            if session.get(Video, video_id) is None:
                log.info(
                    "transcription write skipped for deleted/cancelled video %s during commit",
                    video_id,
                )
                return
            raise
        log.info(
            "inserted %d transcript words and %d sentences for video %s",
            len(word_rows),
            len(sentence_rows),
            video_id,
        )
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def run_slide_extraction(session: Session, video_id: int) -> int:
    from app.models.video import SlideFrame
    from app.services.slide_extraction import SlideExtractor
    from app.services.storage import StorageService

    video = session.get(Video, video_id)
    if not video or not video.storage_path:
        raise ValueError(f"Video {video_id} has no storage_path")

    storage = StorageService()
    extractor = SlideExtractor()

    ext = os.path.splitext(video.storage_path)[1] or ".mp4"
    tmp_video = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    try:
        storage.download_to_fileobj(video.storage_path, tmp_video)
        tmp_video.close()
        results = extractor.process_video(tmp_video.name)

        locked_video = lock_video_for_write(session, video_id)
        if locked_video is None or is_cancelled_or_deleted(session, video_id):
            log.info(
                "slide extraction finished but video %s was deleted/cancelled; skipping DB write",
                video_id,
            )
            return 0

        frame_paths: list[str] = []
        for idx, result in enumerate(results):
            if is_cancelled_or_deleted(session, video_id):
                log.info(
                    "slide extraction cancelled for video %s before frame upload; skipping remaining writes",
                    video_id,
                )
                return 0
            frame_paths.append(result.frame_path)

            frame_key = storage.generate_slide_frame_key(video_id, idx)
            with open(result.frame_path, "rb") as f:
                storage.upload_fileobj(f, frame_key, content_type="image/jpeg")

            slide_frame = SlideFrame(
                video_id=video_id,
                frame_path=frame_key,
                ocr_text=result.ocr_text or None,
                start_time=result.start_time,
                end_time=result.end_time,
            )
            session.add(slide_frame)

        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            if session.get(Video, video_id) is None:
                log.info(
                    "slide frame write skipped for deleted/cancelled video %s during commit",
                    video_id,
                )
                return 0
            raise
        log.info(
            "Slide extraction complete for video %s: %d frames stored",
            video_id,
            len(results),
        )
        return len(results)

    finally:
        extractor.cleanup(tmp_video.name)
        if "results" in locals():
            extractor.cleanup(*(r.frame_path for r in results))


@shared_task
def extract_audio(video_id: int, video_path: str):
    log.info("extracting audio for video %s", video_id)
    session = SyncSession()
    try:
        return run_audio_extraction(session, video_id)
    finally:
        session.close()


@shared_task
def segment_transcript(video_id: int):
    log.info("segmenting transcript for video %s", video_id)
    session = SyncSession()
    try:
        return run_segmentation(session, video_id)
    finally:
        session.close()


@shared_task(bind=True, max_retries=1, default_retry_delay=30)
def create_embeddings(self, video_id: int):
    log.info("creating embeddings for video %s", video_id)
    session = SyncSession()
    try:
        run_embedding(session, video_id)
        log.info("create_embeddings complete for video %s", video_id)
        return {"branch": "embedding", "status": "done"}
    except Exception as exc:
        log.error(
            "create_embeddings failed for video %s: %s: %s",
            video_id,
            type(exc).__name__,
            safe_exception_message(exc),
        )
        session.rollback()
        raise self.retry(exc=exc, countdown=30)
    finally:
        session.close()


def run_embedding(session: Session, video_id: int) -> None:
    from app.models.video import Chunk, Segment, Sentence, SlideFrame
    from app.services.chunking import ChunkingService
    from app.services.qdrant_client import QdrantService

    video = session.get(Video, video_id)
    if not video:
        raise ValueError(f"Video {video_id} not found")

    t0 = time.perf_counter()

    sentences = (
        session.execute(
            select(Sentence).where(Sentence.video_id == video_id).order_by(Sentence.start_time)
        )
        .scalars()
        .all()
    )

    frames = (
        session.execute(select(SlideFrame).where(SlideFrame.video_id == video_id)).scalars().all()
    )

    segs = (
        session.execute(
            select(Segment).where(Segment.video_id == video_id).order_by(Segment.start_time)
        )
        .scalars()
        .all()
    )

    log.info(
        "video %s: loaded %d sentences, %d frames, %d segments in %.2fs",
        video_id,
        len(sentences),
        len(frames),
        len(segs),
        time.perf_counter() - t0,
    )

    sentence_dicts = [
        {"text": s.text, "start_time": s.start_time, "end_time": s.end_time} for s in sentences
    ]
    frame_dicts = [
        {"ocr_text": f.ocr_text, "start_time": f.start_time, "end_time": f.end_time} for f in frames
    ]
    seg_dicts = [
        {"title": s.title, "start_time": s.start_time, "end_time": s.end_time} for s in segs
    ]

    duration = video.duration or 0.0

    t1 = time.perf_counter()
    chunker = ChunkingService()
    chunks = chunker.create_chunks(
        sentence_dicts,
        duration,
        slide_frames=frame_dicts,
        segments=seg_dicts,
        video_title=video.title,
    )
    log.info(
        "video %s: created %d chunks in %.2fs", video_id, len(chunks), time.perf_counter() - t1
    )

    # wipe existing chunks for this video then reinsert fresh
    t2 = time.perf_counter()
    session.query(Chunk).filter(Chunk.video_id == video_id).delete(synchronize_session=False)

    chunk_rows = [
        Chunk(
            video_id=video_id,
            text=c["text"],
            start_time=c["start_time"],
            end_time=c["end_time"],
            slide_text=c["slide_text"] or None,
            position_category=c["position_category"],
            section_title=c.get("section_title", ""),
            context_template=c["context_template"],
        )
        for c in chunks
    ]
    session.add_all(chunk_rows)
    session.commit()
    log.info(
        "video %s: persisted %d chunks in %.2fs",
        video_id,
        len(chunk_rows),
        time.perf_counter() - t2,
    )

    context_texts = [c["context_template"] for c in chunks]

    t3 = time.perf_counter()
    embedder = get_embedder()
    vectors = embedder.embed_texts(context_texts)
    log.info(
        "video %s: embedded %d chunks in %.2fs", video_id, len(vectors), time.perf_counter() - t3
    )

    t4 = time.perf_counter()
    sparse_vecs = embedder.bm25_encode(context_texts)
    log.info("video %s: bm25 encoded in %.2fs", video_id, time.perf_counter() - t4)

    t5 = time.perf_counter()
    qdrant = QdrantService()
    qdrant.ensure_collection_with_sparse()

    upsert_data = []
    for chunk, vec, sparse in zip(chunks, vectors, sparse_vecs):
        point_id = video_id * 1_000_000 + chunk["index"]
        upsert_data.append(
            {
                "id": point_id,
                "vector": vec,
                "sparse_vector": sparse,
                "payload": {
                    "video_id": video_id,
                    "text": chunk["text"],
                    "start_time": chunk["start_time"],
                    "end_time": chunk["end_time"],
                    "position_category": chunk["position_category"],
                    "slide_text": chunk["slide_text"] or "",
                    "section_title": chunk.get("section_title", ""),
                },
            }
        )

    qdrant.upsert_chunks(upsert_data)
    log.info(
        "video %s: upserted %d points to qdrant in %.2fs",
        video_id,
        len(upsert_data),
        time.perf_counter() - t5,
    )
