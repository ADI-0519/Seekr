import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.firebase_auth import get_authenticated_user
from app.core.rate_limit import limiter
from app.core.utils import resolve_owner_uid
from app.crud.video import ProcessingJobService, VideoService
from app.db.session import get_db
from app.models.video import ProcessingStatus
from app.schemas.job import JobCancelResponse, JobResponse, JobTriggerResponse
from app.tasks.video_tasks import process_video

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/{video_id}", response_model=JobTriggerResponse, status_code=202)
@limiter.limit("10/hour")
async def trigger_processing(
    request: Request,
    video_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    video_svc = VideoService(db)
    owner_uid = resolve_owner_uid(current_user)
    video = await video_svc.get_by_id(video_id, owner_uid=owner_uid)
    if not video:
        raise HTTPException(404, "Video not found")

    job_svc = ProcessingJobService(db)
    existing_jobs = await job_svc.get_by_video(video_id, owner_uid=owner_uid)
    # check if theres already an active job running
    for job in existing_jobs:
        if job.status in ("queued", "running"):
            raise HTTPException(409, "Video already has an active processing job")

    task_id = str(uuid.uuid4())
    await job_svc.create(video_id, task_id=task_id)
    process_video.apply_async(args=[video_id], task_id=task_id)

    return JobTriggerResponse(
        video_id=video_id,
        task_id=task_id,
        message="Processing queued",
    )


@router.get("/{video_id}", response_model=JobResponse)
@limiter.limit("120/minute")
async def get_job_status(
    request: Request,
    video_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    owner_uid = resolve_owner_uid(current_user)
    video_svc = VideoService(db)
    if not await video_svc.get_by_id(video_id, owner_uid=owner_uid):
        raise HTTPException(404, "Video not found")

    job_svc = ProcessingJobService(db)
    jobs = await job_svc.get_by_video(video_id, owner_uid=owner_uid)
    if not jobs:
        raise HTTPException(404, "No processing job found for this video")

    # return the most recent job (list is already sorted desc by created_at)
    return JobResponse.model_validate(jobs[0])


@router.post("/{video_id}/cancel", response_model=JobCancelResponse)
@limiter.limit("20/hour")
async def cancel_job(
    request: Request,
    video_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_authenticated_user),
):
    video_svc = VideoService(db)
    owner_uid = resolve_owner_uid(current_user)
    video = await video_svc.get_by_id(video_id, owner_uid=owner_uid)
    if not video:
        raise HTTPException(404, "Video not found")

    job_svc = ProcessingJobService(db)
    jobs = await job_svc.get_by_video(video_id, owner_uid=owner_uid)
    if not jobs:
        raise HTTPException(404, "No processing job found for this video")

    job = jobs[0]
    if job.status in ("done", "failed", "cancelled"):
        raise HTTPException(409, f"Cannot cancel a job with status '{job.status}'")
    if not job.task_id:
        raise HTTPException(409, "Job has no task id and cannot be cancelled")

    celery_app.control.revoke(job.task_id, terminate=True)
    await job_svc.update_status(
        job.id,
        status="cancelled",
        stage=job.current_stage,
        error="Processing cancelled by user",
    )

    # Keep the video row during cancellation so in-flight parallel workers
    # can observe cancelled state and exit without foreign-key races.
    video.status = ProcessingStatus.FAILED.value
    video.error_message = "Processing cancelled by user"
    await db.commit()

    return JobCancelResponse(
        video_id=video_id,
        task_id=job.task_id,
        status="cancelled",
        message="Processing cancelled",
    )
