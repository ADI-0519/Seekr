from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import case, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.video import (
    ChatMessage,
    ProcessingJob,
    ProcessingStatus,
    Segment,
    Sentence,
    SlideFrame,
    Video,
)

OWNER_UNSCOPED = object()


def with_owner_scope(stmt, owner_uid=OWNER_UNSCOPED):
    # Distinguish "no owner filter" from an explicit NULL owner_uid lookup.
    if owner_uid is OWNER_UNSCOPED:
        return stmt
    return stmt.where(Video.owner_uid == owner_uid)


class VideoService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        title: str,
        youtube_url: Optional[str] = None,
        owner_uid: Optional[str] = None,
    ):
        video = Video(
            title=title,
            youtube_url=youtube_url,
            owner_uid=owner_uid,
            status=ProcessingStatus.PENDING,
        )
        self.db.add(video)
        await self.db.flush()
        return video

    async def get_by_id(self, id: int, owner_uid=OWNER_UNSCOPED):
        stmt = with_owner_scope(select(Video).where(Video.id == id), owner_uid)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def owns_storage_key(self, key: str, owner_uid: str) -> bool:
        """Return whether a storage object is referenced by one of the owner's videos."""
        stmt = (
            select(Video.id)
            .where(
                Video.owner_uid == owner_uid,
                or_(
                    Video.storage_path == key,
                    Video.audio_path == key,
                    Video.thumbnail_path == key,
                    Video.slide_frames.any(SlideFrame.frame_path == key),
                ),
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_completed_by_url(self, url: str, owner_uid=OWNER_UNSCOPED):
        # exact URL match on completed videos only, no point returning a failed or in-progress one
        stmt = select(Video).where(
            Video.youtube_url == url,
            Video.status == ProcessingStatus.COMPLETE.value,
        )
        stmt = with_owner_scope(stmt, owner_uid)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_with_relations(self, id: int, owner_uid=OWNER_UNSCOPED):
        stmt = (
            select(Video)
            .options(selectinload(Video.sentences), selectinload(Video.segments))
            .where(Video.id == id)
        )
        stmt = with_owner_scope(stmt, owner_uid)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_for_delete(self, id: int, owner_uid=OWNER_UNSCOPED):
        stmt = (
            select(Video)
            .options(
                selectinload(Video.sentences),
                selectinload(Video.transcript_words),
                selectinload(Video.segments),
                selectinload(Video.chunks),
                selectinload(Video.slide_frames),
                selectinload(Video.jobs),
            )
            .where(Video.id == id)
        )

        stmt = with_owner_scope(stmt, owner_uid)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def update_status(
        self,
        id: int,
        status: ProcessingStatus,
        error: Optional[str] = None,
        owner_uid=OWNER_UNSCOPED,
    ):
        video = await self.get_by_id(id, owner_uid=owner_uid)

        if video:
            video.status = status
            video.error_message = error
            await self.db.flush()
        return video

    async def update_playback_position(
        self, id: int, position_seconds: float, owner_uid=OWNER_UNSCOPED
    ):
        video = await self.get_by_id(id, owner_uid=owner_uid)
        if not video:
            return None

        clamped_position = max(0.0, float(position_seconds))
        if video.duration is not None:
            clamped_position = min(clamped_position, float(video.duration))

        video.last_playback_position = clamped_position
        await self.db.flush()
        return video

    async def list_videos(self, skip=0, limit=20, owner_uid=OWNER_UNSCOPED):
        stmt = select(Video).order_by(Video.created_at.desc()).offset(skip).limit(limit)
        stmt = with_owner_scope(stmt, owner_uid)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_profile_summary(self, owner_uid=OWNER_UNSCOPED, recent_limit: int = 5):
        summary_stmt = select(
            func.count(Video.id).label("lecture_count"),
            func.coalesce(
                func.sum(case((Video.status == ProcessingStatus.COMPLETE.value, 1), else_=0)),
                0,
            ).label("ready_lecture_count"),
            func.coalesce(
                func.sum(case((Video.status == ProcessingStatus.FAILED.value, 1), else_=0)),
                0,
            ).label("failed_lecture_count"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            Video.status.in_(
                                [
                                    ProcessingStatus.COMPLETE.value,
                                    ProcessingStatus.FAILED.value,
                                ]
                            ),
                            0,
                        ),
                        else_=1,
                    )
                ),
                0,
            ).label("processing_lecture_count"),
            func.coalesce(func.sum(Video.duration), 0.0).label("total_duration_seconds"),
        ).select_from(Video)
        summary_stmt = with_owner_scope(summary_stmt, owner_uid)
        summary = (await self.db.execute(summary_stmt)).mappings().one()

        recent_uploads = await self.list_videos(skip=0, limit=recent_limit, owner_uid=owner_uid)

        return {
            "lecture_count": int(summary["lecture_count"] or 0),
            "ready_lecture_count": int(summary["ready_lecture_count"] or 0),
            "processing_lecture_count": int(summary["processing_lecture_count"] or 0),
            "failed_lecture_count": int(summary["failed_lecture_count"] or 0),
            "total_duration_seconds": float(summary["total_duration_seconds"] or 0.0),
            "recent_uploads": recent_uploads,
        }

    async def delete(self, id: int, owner_uid=OWNER_UNSCOPED):
        video = await self.get_for_delete(id, owner_uid=owner_uid)

        if video:
            await self.db.delete(video)
            await self.db.flush()
        return video

    async def delete_instance(self, video: Video):
        if video:
            await self.db.delete(video)
            await self.db.flush()
        return video


class SentenceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_many(self, video_id: int, sentences: list[dict]):
        for s in sentences:
            self.db.add(
                Sentence(
                    video_id=video_id,
                    text=s["text"],
                    start_time=s["start_time"],
                    end_time=s["end_time"],
                    confidence=s.get("confidence"),
                )
            )
        await self.db.flush()

    async def get_by_video(self, video_id: int):
        stmt = select(Sentence).where(Sentence.video_id == video_id).order_by(Sentence.start_time)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())


class SegmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_many(self, video_id: int, segments: list[dict]):
        for s in segments:
            self.db.add(
                Segment(
                    video_id=video_id,
                    title=s["title"],
                    summary=s.get("summary"),
                    start_time=s["start_time"],
                    end_time=s["end_time"],
                )
            )
        await self.db.flush()

    async def get_by_video(self, video_id: int):
        stmt = select(Segment).where(Segment.video_id == video_id).order_by(Segment.start_time)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def save_notes(self, notes: list[dict]) -> None:
        for item in notes:
            stmt = (
                update(Segment)
                .where(Segment.id == item["segment_id"])
                .values(notes_markdown=item["notes_markdown"])
            )
            await self.db.execute(stmt)


class SlideFrameService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_many(self, video_id: int, frames: list[dict]):
        for f in frames:
            self.db.add(
                SlideFrame(
                    video_id=video_id,
                    frame_path=f["frame_path"],
                    ocr_text=f.get("ocr_text"),
                    start_time=f["start_time"],
                    end_time=f["end_time"],
                )
            )
        await self.db.flush()

    async def get_by_video(self, video_id: int):
        stmt = (
            select(SlideFrame)
            .where(SlideFrame.video_id == video_id)
            .order_by(SlideFrame.start_time)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_by_video_paginated(
        self, video_id: int, offset: int = 0, limit: int = 50
    ) -> tuple[list[SlideFrame], int]:
        # count first so we don't need a second round-trip for total
        count_stmt = (
            select(func.count()).select_from(SlideFrame).where(SlideFrame.video_id == video_id)
        )
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = (
            select(SlideFrame)
            .where(SlideFrame.video_id == video_id)
            .order_by(SlideFrame.start_time)
            .offset(offset)
            .limit(limit)
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        return rows, total

    async def get_by_time_range(self, video_id: int, start: float, end: float) -> list[SlideFrame]:
        # overlapping interval check
        stmt = (
            select(SlideFrame)
            .where(
                SlideFrame.video_id == video_id,
                SlideFrame.start_time < end,
                SlideFrame.end_time > start,
            )
            .order_by(SlideFrame.start_time)
        )
        return list((await self.db.execute(stmt)).scalars().all())


class ProcessingJobService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, video_id: int, task_id: Optional[str] = None):
        job = ProcessingJob(video_id=video_id, task_id=task_id, status="queued")
        self.db.add(job)
        await self.db.flush()
        return job

    async def get_by_video(self, video_id: int, owner_uid=OWNER_UNSCOPED):
        stmt = select(ProcessingJob).where(ProcessingJob.video_id == video_id)
        if owner_uid is not OWNER_UNSCOPED:
            stmt = stmt.join(Video, Video.id == ProcessingJob.video_id).where(
                Video.owner_uid == owner_uid
            )
        stmt = stmt.order_by(ProcessingJob.created_at.desc())

        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def update_status(
        self, job_id: int, status: str, stage: Optional[str] = None, error: Optional[str] = None
    ):
        stmt = select(ProcessingJob).where(ProcessingJob.id == job_id)
        res = await self.db.execute(stmt)
        job = res.scalar_one_or_none()
        if job:
            job.status = status
            if stage:
                job.current_stage = stage
            if error:
                job.error_message = error
            if status == "running" and not job.started_at:
                job.started_at = datetime.now(timezone.utc)
            if status in ("done", "failed"):
                job.completed_at = datetime.now(timezone.utc)
            await self.db.flush()
        return job


class ChatMessageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_many(self, video_id: int, messages: list[dict]):
        for m in messages:
            self.db.add(
                ChatMessage(
                    video_id=video_id,
                    role=m["role"],
                    text=m.get("text"),
                    mode=m.get("mode"),
                    citations_json=m.get("citations_json"),
                    results_json=m.get("results_json"),
                )
            )
        await self.db.flush()

    async def get_by_video(self, video_id: int):
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.video_id == video_id)
            .order_by(ChatMessage.created_at)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def delete_by_video(self, video_id: int):
        stmt = delete(ChatMessage).where(ChatMessage.video_id == video_id)
        await self.db.execute(stmt)
        await self.db.flush()
