import io
import logging
import uuid
import zipfile
from hashlib import sha1

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.firebase_auth import get_authenticated_user
from app.core.log_safety import safe_exception_message
from app.core.rate_limit import limiter
from app.core.utils import resolve_owner_uid
from app.crud.video import (
    ChatMessageService,
    ProcessingJobService,
    SegmentService,
    SentenceService,
    SlideFrameService,
    VideoService,
)
from app.db.session import get_db
from app.models.video import (
    Chunk,
    ProcessingJob,
    ProcessingStatus,
    Segment,
    Sentence,
    SlideFrame,
    TranscriptWord,
    Video,
)
from app.schemas.video import (
    ChatHistoryRequest,
    ChatMessageResponse,
    Citation,
    GeneratedNoteItem,
    LinkSubmitRequest,
    NotesExportRequest,
    NotesListResponse,
    PlaybackPositionRequest,
    PlaybackPositionResponse,
    QueryRequest,
    QueryResponse,
    SearchResult,
    SegmentResponse,
    SentenceResponse,
    SlideFrameResponse,
    SlideListResponse,
    TranscriptResponse,
    VideoResponse,
    VideoStatusResponse,
)
from app.services.cache import CacheService, get_redis
from app.services.notes_generation import NotesGenerator, NotesInput, NotesResult
from app.services.pdf_export import generate_notes_pdf
from app.services.qdrant_client import QdrantService
from app.services.query_router import classify_query
from app.services.storage import StorageService
from app.services.video_acquisition import (
    infer_video_content_type,
    measure_file_size,
    validate_file_extension,
    validate_file_mimetype,
)
from app.tasks.retrieval_tasks import run_query
from app.tasks.video_tasks import process_video

log = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["videos"])


def serialise(data: dict) -> dict:
    return {k: v.isoformat() if hasattr(v, "isoformat") else v for k, v in data.items()}


def resolve_upload_size(file: UploadFile) -> int | None:
    if file.size is not None:
        return int(file.size)
    return measure_file_size(file.file)


def to_video_response(video: Video) -> VideoResponse:
    payload = VideoResponse.model_validate(video).model_dump()
    settings = get_settings()

    try:
        storage = StorageService()
    except Exception:
        storage = None

    if storage:
        ttl = settings.storage_presigned_ttl_seconds
        if video.storage_path:
            try:
                video_url = storage.get_presigned_url(video.storage_path, expires=ttl)
                payload["video_url"] = video_url if isinstance(video_url, str) else None
            except Exception:
                payload["video_url"] = None
        if video.thumbnail_path:
            try:
                thumbnail_url = storage.get_presigned_url(video.thumbnail_path, expires=ttl)
                payload["thumbnail_url"] = thumbnail_url if isinstance(thumbnail_url, str) else None
            except Exception:
                payload["thumbnail_url"] = None

    return VideoResponse(**payload)


async def get_presigned_url_cached(
    storage: StorageService, path: str, ttl: int, cache: CacheService | None
) -> str | None:
    cache_key = f"presigned:{path}"
    if cache:
        try:
            cached = await cache.get(cache_key)
            if isinstance(cached, str) and cached:
                return cached
        except Exception:
            pass
    try:
        url = storage.get_presigned_url(path, expires=ttl)
        if not isinstance(url, str):
            return None
        if cache:
            try:
                # cache for less than URL's own TTL so we never serve an expired one
                await cache.set(cache_key, url, ttl=86400)
            except Exception:
                pass
        return url
    except Exception:
        return None


async def get_owned_video_or_404(
    video_id: int,
    db: AsyncSession,
    owner_uid: str | None,
) -> Video:
    repo = VideoService(db)
    video = await repo.get_by_id(video_id, owner_uid=owner_uid)
    if not isinstance(video, Video):
        raise HTTPException(404, "Video not found")
    return video


@router.post("/upload", response_model=VideoResponse)
@limiter.limit("10/hour")
async def upload_video(
    request: Request,
    title: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    settings = get_settings()
    max_bytes = settings.storage_max_file_size_mb * 1024 * 1024
    upload_size = resolve_upload_size(file)
    if upload_size is not None and upload_size > max_bytes:
        raise HTTPException(
            400, f"File exceeds the maximum allowed size of {settings.storage_max_file_size_mb} MB"
        )

    if not validate_file_extension(file.filename or ""):
        raise HTTPException(400, "Unsupported file format")

    header = await file.read(16)
    if not validate_file_mimetype(header):
        raise HTTPException(400, "File content does not match a supported video format")
    await file.seek(0)

    repo = VideoService(db)
    owner_uid = resolve_owner_uid(current_user)
    video = await repo.create(title, None, owner_uid=owner_uid)

    storage = StorageService()
    storage.ensure_bucket_exists()
    key = storage.generate_object_key(video.id, file.filename)
    content_type = infer_video_content_type(file.filename or "")

    try:
        file.file.seek(0)
        storage.upload_fileobj(file.file, key, content_type=content_type)
    except Exception as e:
        safe_message = safe_exception_message(e, fallback="Storage upload failed.")
        log.error("storage upload failed: %s: %s", type(e).__name__, safe_message)
        await repo.update_status(video.id, ProcessingStatus.FAILED, safe_message)
        raise HTTPException(500, "Failed to upload file")

    video.storage_path = key
    await db.flush()

    task_id = str(uuid.uuid4())
    await ProcessingJobService(db).create(video.id, task_id=task_id)
    await db.commit()
    await db.refresh(video)
    process_video.apply_async(args=[video.id], task_id=task_id)
    return to_video_response(video)


@router.post("/link", response_model=VideoResponse, status_code=201)
@limiter.limit("10/hour")
async def submit_link(
    request: Request,
    req: LinkSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    repo = VideoService(db)
    owner_uid = resolve_owner_uid(current_user)

    # if this URL was already processed successfully, return it with from_cache=True
    existing = await repo.get_completed_by_url(str(req.url), owner_uid=owner_uid)
    if existing:
        await db.refresh(existing)
        data = to_video_response(existing).model_dump()
        data["from_cache"] = True
        return JSONResponse(
            content=serialise(data), status_code=200
        )  # 200 rather than 201 since nothing was created

    title = req.title or "Imported Video"
    video = await repo.create(title, str(req.url), owner_uid=owner_uid)

    task_id = str(uuid.uuid4())
    await ProcessingJobService(db).create(video.id, task_id=task_id)
    await db.commit()
    await db.refresh(video)
    process_video.apply_async(args=[video.id], task_id=task_id)
    return to_video_response(video)


@router.post("/youtube", response_model=VideoResponse, status_code=201)
@limiter.limit("10/hour")
async def submit_youtube(
    request: Request,
    req: LinkSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    return await submit_link(request, req, db, current_user)


@router.get("/{video_id}/stream")
async def stream_video(
    request: Request,
    video_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    owner_uid = resolve_owner_uid(current_user)
    video = await get_owned_video_or_404(video_id, db, owner_uid)
    if not video.storage_path:
        raise HTTPException(404, "No video file available")
    range_header = request.headers.get("Range")
    storage = StorageService()

    try:
        body, content_type, content_length, content_range = storage.get_object_stream(
            video.storage_path, range_header=range_header
        )
    except Exception as e:
        if "InvalidRange" in str(e):
            raise HTTPException(status_code=416, detail="Requested Range Not Satisfiable")
        log.error(
            "video stream error for video %s: %s: %s",
            video_id,
            type(e).__name__,
            safe_exception_message(e),
        )
        raise HTTPException(status_code=500, detail="Failed to stream video")

    headers = {
        "Accept-Ranges": "bytes",
    }
    if content_length:
        headers["Content-Length"] = str(content_length)
    if content_range:
        headers["Content-Range"] = content_range
        status_code = 206
    else:
        status_code = 200

    return StreamingResponse(
        body, media_type=content_type, headers=headers, status_code=status_code
    )


@router.get("/{video_id}/thumbnail")
async def get_thumbnail(
    video_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    owner_uid = resolve_owner_uid(current_user)
    video = await get_owned_video_or_404(video_id, db, owner_uid)
    if not video.thumbnail_path:
        raise HTTPException(404, "No thumbnail available")
    storage = StorageService()
    body, _ct, content_length, _cr = storage.get_object_stream(video.thumbnail_path)
    headers = {}
    if content_length:
        headers["Content-Length"] = str(content_length)
    return StreamingResponse(body, media_type="image/jpeg", headers=headers)


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    owner_uid = resolve_owner_uid(current_user)
    video = await get_owned_video_or_404(video_id, db, owner_uid)
    return to_video_response(video)


@router.delete("/{video_id}", status_code=204)
async def delete_video(
    video_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    owner_uid = resolve_owner_uid(current_user)
    video = await get_owned_video_or_404(video_id, db, owner_uid)

    log.info("Deleting video %s", video_id)

    slide_frame_keys = list(
        (await db.execute(select(SlideFrame.frame_path).where(SlideFrame.video_id == video_id)))
        .scalars()
        .all()
    )

    job_svc = ProcessingJobService(db)
    jobs = await job_svc.get_by_video(video_id, owner_uid=owner_uid)
    latest_job = jobs[0] if jobs else None
    if latest_job and latest_job.status in ("queued", "running") and latest_job.task_id:
        try:
            process_video.app.control.revoke(latest_job.task_id, terminate=True)
            await job_svc.update_status(
                latest_job.id,
                status="cancelled",
                stage=latest_job.current_stage,
                error="Lecture deleted by user",
            )
        except Exception as exc:
            log.warning(
                "failed to revoke task %s while deleting video %s: %s: %s",
                latest_job.task_id,
                video_id,
                type(exc).__name__,
                safe_exception_message(exc),
            )

    storage_keys = {
        key
        for key in (
            video.storage_path,
            video.audio_path,
            video.thumbnail_path,
            *slide_frame_keys,
        )
        if key
    }
    if storage_keys:
        try:
            storage = StorageService()
        except Exception as exc:
            log.warning(
                "storage cleanup unavailable while deleting video %s: %s: %s",
                video_id,
                type(exc).__name__,
                safe_exception_message(exc),
            )
        else:
            for key in storage_keys:
                try:
                    storage.delete_object(key)
                except Exception as exc:
                    log.warning(
                        "failed to delete storage object %s for video %s: %s: %s",
                        key,
                        video_id,
                        type(exc).__name__,
                        safe_exception_message(exc),
                    )

    try:
        QdrantService().delete_video_points(video_id)
    except Exception as exc:
        log.warning(
            "failed to delete qdrant points for video %s: %s: %s",
            video_id,
            type(exc).__name__,
            safe_exception_message(exc),
        )

    try:
        for model in (SlideFrame, Sentence, Segment, TranscriptWord, Chunk, ProcessingJob):
            await db.execute(delete(model).where(model.video_id == video_id))
        delete_stmt = delete(Video).where(Video.id == video_id)
        if owner_uid is None:
            delete_stmt = delete_stmt.where(Video.owner_uid.is_(None))
        else:
            delete_stmt = delete_stmt.where(Video.owner_uid == owner_uid)
        await db.execute(delete_stmt)
        await db.commit()
    except Exception as exc:
        await db.rollback()
        log.error(
            "failed to delete video %s: %s: %s",
            video_id,
            type(exc).__name__,
            safe_exception_message(exc),
        )
        raise HTTPException(500, "Failed to delete video") from exc

    log.info("Deleted video %s", video_id)
    return Response(status_code=204)


@router.get("/{video_id}/status", response_model=VideoStatusResponse)
async def get_status(
    video_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    owner_uid = resolve_owner_uid(current_user)
    video = await get_owned_video_or_404(video_id, db, owner_uid)

    # get current stage from processing job if available
    job_svc = ProcessingJobService(db)
    jobs = await job_svc.get_by_video(video_id, owner_uid=owner_uid)
    current_stage = jobs[0].current_stage if jobs else None
    transcription_stage = jobs[0].transcription_stage if jobs else None
    slides_stage = jobs[0].slides_stage if jobs else None

    return VideoStatusResponse(
        id=video.id,
        status=video.status,
        current_stage=current_stage,
        transcription_stage=transcription_stage,
        slides_stage=slides_stage,
        error_message=video.error_message,
    )


@router.get("/{video_id}/playback", response_model=PlaybackPositionResponse)
async def get_playback_position(
    video_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    owner_uid = resolve_owner_uid(current_user)
    video = await get_owned_video_or_404(video_id, db, owner_uid)
    return PlaybackPositionResponse(
        video_id=video.id,
        position_seconds=max(0.0, float(video.last_playback_position or 0.0)),
    )


@router.put("/{video_id}/playback", response_model=PlaybackPositionResponse)
@limiter.limit("120/minute")
async def update_playback_position(
    request: Request,
    video_id: int,
    payload: PlaybackPositionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    owner_uid = resolve_owner_uid(current_user)
    video = await get_owned_video_or_404(video_id, db, owner_uid)
    resolved_video_id = int(video.id)

    updated = await VideoService(db).update_playback_position(
        video.id, payload.position_seconds, owner_uid=owner_uid
    )
    resolved_position = max(
        0.0, float(updated.last_playback_position if updated else payload.position_seconds)
    )
    await db.commit()

    return PlaybackPositionResponse(
        video_id=resolved_video_id,
        position_seconds=resolved_position,
    )


@router.get("/{video_id}/transcript", response_model=TranscriptResponse)
async def get_transcript(
    video_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    owner_uid = resolve_owner_uid(current_user)
    await get_owned_video_or_404(video_id, db, owner_uid)

    sentences = await SentenceService(db).get_by_video(video_id)
    segments = await SegmentService(db).get_by_video(video_id)

    return TranscriptResponse(
        video_id=video_id,
        sentences=[SentenceResponse.model_validate(s) for s in sentences],
        segments=[SegmentResponse.model_validate(s) for s in segments],
    )


@router.get("/{video_id}/segments")
async def get_segments(
    video_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    owner_uid = resolve_owner_uid(current_user)
    await get_owned_video_or_404(video_id, db, owner_uid)

    segments = await SegmentService(db).get_by_video(video_id)
    return [SegmentResponse.model_validate(s) for s in segments]


@router.post("/{video_id}/query", response_model=QueryResponse)
@limiter.limit("30/minute")
async def unified_query(
    request: Request,
    video_id: int,
    req: QueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    owner_uid = resolve_owner_uid(current_user)
    await get_owned_video_or_404(video_id, db, owner_uid)

    # resolve mode before checking cache so we know to look for cached results or not
    resolved = req.mode if req.mode != "auto" else classify_query(req.query)

    if resolved == "retrieval":
        query_key = sha1(req.query.strip().lower().encode()).hexdigest()
        cache_key = f"search:{owner_uid}:{video_id}:{query_key}"

        try:
            cache = CacheService(await get_redis())
            cached = await cache.get(cache_key)
            if cached is not None:
                return QueryResponse(
                    query=req.query,
                    mode="retrieval",
                    results=[SearchResult(**r) for r in cached],
                )
        except Exception:
            cache = None

        task = run_query.delay(video_id, req.query, "retrieval", req.top_k)
        try:
            result = task.get(timeout=60)
        except Exception:
            raise HTTPException(504, "Search is taking too long. Please try again in a moment.")

        results = [SearchResult(**h) for h in result["results"]]

        if cache is not None:
            try:
                await cache.set(
                    cache_key, [r.model_dump() for r in results], ttl=CacheService.SEARCH_TTL
                )
            except Exception:
                pass

        return QueryResponse(query=req.query, mode="retrieval", results=results)

    # qa path - no caching since answers can be verbose and vary by context
    task = run_query.delay(video_id, req.query, "qa", req.top_k)
    try:
        result = task.get(timeout=60)
    except Exception:
        raise HTTPException(
            status_code=504, detail="QA is taking too long. Please try again in a moment."
        )

    return QueryResponse(
        query=req.query,
        mode="qa",
        answer=result["answer"],
        citations=[Citation(**c) for c in result["citations"]],
    )


@router.get("/")
async def list_all(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    repo = VideoService(db)
    owner_uid = resolve_owner_uid(current_user)
    videos = await repo.list_videos(skip, limit, owner_uid=owner_uid)
    # build presigned URLs with redis caching to one storage call per video per request
    try:
        cache = CacheService(await get_redis())
    except Exception:
        cache = None

    try:
        storage = StorageService()
    except Exception:
        storage = None

    settings = get_settings()
    ttl = settings.storage_presigned_ttl_seconds

    result = []
    for video in videos:
        payload = VideoResponse.model_validate(video).model_dump()
        if storage:
            if video.storage_path:
                payload["video_url"] = await get_presigned_url_cached(
                    storage, video.storage_path, ttl, cache
                )
            if video.thumbnail_path:
                payload["thumbnail_url"] = await get_presigned_url_cached(
                    storage, video.thumbnail_path, ttl, cache
                )
        result.append(VideoResponse(**payload))
    return result


@router.get("/{video_id}/slides", response_model=SlideListResponse)
async def get_slides(
    video_id: int,
    offset: int = 0,
    limit: int = 50,
    start_time: float | None = None,
    end_time: float | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    owner_uid = resolve_owner_uid(current_user)
    await get_owned_video_or_404(video_id, db, owner_uid)

    svc = SlideFrameService(db)
    storage = StorageService()

    if start_time is not None and end_time is not None:
        if start_time >= end_time:
            raise HTTPException(400, "start_time must be less than end_time")
        frames = await svc.get_by_time_range(video_id, start_time, end_time)
        total = len(frames)
        # still page it so the response shape stays consistent
        frames = frames[offset : offset + limit]
    else:
        frames, total = await svc.get_by_video_paginated(video_id, offset, limit)

    slides = []
    for f in frames:
        frame_url = None
        if f.frame_path:
            try:
                frame_url = storage.get_presigned_url(f.frame_path)
            except Exception:
                # minio might be down, soreturn the raw path so frontend can still display metadata
                frame_url = f.frame_path

        slides.append(
            SlideFrameResponse(
                id=f.id,
                start_time=f.start_time,
                end_time=f.end_time,
                ocr_text=f.ocr_text,
                frame_url=frame_url,
            )
        )

    return SlideListResponse(video_id=video_id, total=total, slides=slides)


@router.get("/{video_id}/slides/download")
@limiter.limit("20/hour")
async def download_slides(
    request: Request,
    video_id: int,
    start_time: float | None = None,
    end_time: float | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    owner_uid = resolve_owner_uid(current_user)
    await get_owned_video_or_404(video_id, db, owner_uid)

    svc = SlideFrameService(db)
    storage = StorageService()

    if start_time is not None and end_time is not None:
        if start_time >= end_time:
            raise HTTPException(400, "start_time must be less than end_time")
        frames = await svc.get_by_time_range(video_id, start_time, end_time)
    else:
        frames, _ = await svc.get_by_video_paginated(video_id, 0, 1000)

    downloadable_frames = [f for f in frames if f.frame_path]
    if not downloadable_frames:
        raise HTTPException(404, "No slide frames available")

    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for frame in downloadable_frames:
            temp_buf = io.BytesIO()
            try:
                if not frame.frame_path:
                    continue
                storage.download_to_fileobj(frame.frame_path, temp_buf)
            except Exception:
                continue
            temp_buf.seek(0)
            name = f"slide_{frame.id}_{int(frame.start_time):05d}.jpg"
            archive.writestr(name, temp_buf.read())

    archive_buffer.seek(0)
    headers = {
        "Content-Disposition": f'attachment; filename="slides-{video_id}.zip"',
        "Content-Type": "application/zip",
    }
    return StreamingResponse(archive_buffer, headers=headers)


@router.get("/qdrant/health")
async def qdrant_health(
    current_user: dict | None = Depends(get_authenticated_user),
):
    try:
        service = QdrantService()
        service.client.get_collections()
        return {"qdrant": "ok", "collection": service.collection}

    except Exception as e:
        log.warning(
            "qdrant health check failed: %s: %s", type(e).__name__, safe_exception_message(e)
        )
        raise HTTPException(status_code=503, detail="Qdrant is unavailable right now.")


@router.post("/qdrant/seed/{video_id}")
async def seed(
    video_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    # test endpoint to check qdrant works
    settings = get_settings()
    if not settings.debug:
        raise HTTPException(403, "Not available in production")

    try:
        owner_uid = resolve_owner_uid(current_user)
        await get_owned_video_or_404(video_id, db, owner_uid)
        service = QdrantService()
        service.create_collection()
        service.upsert_test_points(video_id=video_id, n=3)
        results = service.search_vector(video_id=video_id, top_k=3)

        # handle both old and new qdrant response formats
        if results and isinstance(results[0], tuple):
            results = [hit for (_, hit) in results]

        return {
            "seeded_video_id": video_id,
            "top_matches": [{"id": r.id, "score": r.score, "payload": r.payload} for r in results],
        }

    except HTTPException:
        raise
    except Exception as e:
        log.error(
            "qdrant test error for video %s: %s: %s",
            video_id,
            type(e).__name__,
            safe_exception_message(e),
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{video_id}/chat", response_model=list[ChatMessageResponse])
async def get_chat_history(
    video_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    owner_uid = resolve_owner_uid(current_user)
    await get_owned_video_or_404(video_id, db, owner_uid)

    svc = ChatMessageService(db)
    messages = await svc.get_by_video(video_id)
    return [ChatMessageResponse.model_validate(m) for m in messages]


@router.put("/{video_id}/chat")
@limiter.limit("60/minute")
async def save_chat_history(
    request: Request,
    video_id: int,
    req: ChatHistoryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    owner_uid = resolve_owner_uid(current_user)
    await get_owned_video_or_404(video_id, db, owner_uid)

    svc = ChatMessageService(db)
    # Replace all existing messages with new ones
    await svc.delete_by_video(video_id)
    await svc.create_many(video_id, [m.model_dump() for m in req.messages])
    await db.commit()
    return {"status": "ok", "saved": len(req.messages)}


async def build_notes_inputs(video_id: int, db: AsyncSession) -> list[NotesInput]:
    segments = await SegmentService(db).get_by_video(video_id)
    sentences = await SentenceService(db).get_by_video(video_id)
    slide_frames = await SlideFrameService(db).get_by_video(video_id)

    inputs: list[NotesInput] = []
    for seg in segments:
        seg_text = " ".join(
            s.text
            for s in sentences
            if s.start_time >= seg.start_time and s.end_time <= seg.end_time
        )

        # aggregate unique OCR lines from slides that overlap this segment
        seen: set[str] = set()
        slide_lines = []
        for frame in slide_frames:
            if frame.start_time >= seg.end_time or frame.end_time <= seg.start_time:
                continue
            for line in (frame.ocr_text or "").split("\n"):
                key = line.strip().lower()
                if key and key not in seen:
                    seen.add(key)
                    slide_lines.append(line.strip())

        inputs.append(
            NotesInput(
                segment_id=seg.id,
                title=seg.title,
                transcript_text=seg_text,
                start_time=seg.start_time,
                end_time=seg.end_time,
                slide_text="\n".join(slide_lines),
            )
        )
    return inputs


@router.get("/{video_id}/notes", response_model=NotesListResponse)
@limiter.limit("20/hour")
async def get_notes(
    request: Request,
    video_id: int,
    regenerate: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    owner_uid = resolve_owner_uid(current_user)
    video = await get_owned_video_or_404(video_id, db, owner_uid)
    if video.status != ProcessingStatus.COMPLETE.value:
        raise HTTPException(400, "Video processing not complete")

    segments = await SegmentService(db).get_by_video(video_id)
    if not segments:
        raise HTTPException(404, "No segments found for this video")

    # return cached notes if all segments have them and regenerate not requested
    if not regenerate and all(s.notes_markdown for s in segments):
        return NotesListResponse(
            video_id=video_id,
            notes=[
                GeneratedNoteItem(
                    segment_id=s.id,
                    title=s.title,
                    notes_markdown=s.notes_markdown,
                    start_time=s.start_time,
                    end_time=s.end_time,
                )
                for s in segments
            ],
        )

    inputs = await build_notes_inputs(video_id, db)
    generator = NotesGenerator()
    results = generator.generate_all(inputs)

    await SegmentService(db).save_notes(
        [{"segment_id": r.segment_id, "notes_markdown": r.notes_markdown} for r in results]
    )
    await db.commit()

    return NotesListResponse(
        video_id=video_id,
        notes=[
            GeneratedNoteItem(
                segment_id=r.segment_id,
                title=r.title,
                notes_markdown=r.notes_markdown,
                start_time=r.start_time,
                end_time=r.end_time,
            )
            for r in results
        ],
    )


@router.post("/{video_id}/notes/export")
@limiter.limit("20/hour")
async def export_notes_pdf(
    request: Request,
    video_id: int,
    req: NotesExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    owner_uid = resolve_owner_uid(current_user)
    video = await get_owned_video_or_404(video_id, db, owner_uid)

    pdf_buffer = generate_notes_pdf(
        lecture_title=video.title,
        notes=[
            NotesResult(
                segment_id=n.segment_id,
                title=n.title,
                notes_markdown=n.notes_markdown,
                start_time=n.start_time,
                end_time=n.end_time,
            )
            for n in req.notes
        ],
        lecture_duration=video.duration,
    )

    safe_title = video.title.replace(" ", "_")[:50]
    filename = f"notes_{safe_title}_{video_id}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
