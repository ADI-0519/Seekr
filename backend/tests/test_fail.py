from unittest.mock import patch

import pytest
from app.db.session import Base
from app.models.video import ProcessingJob, ProcessingStatus, Video
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def sync_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def video_id(sync_session):
    video = Video(
        id=1,
        title="Failure Path Test Video",
        status=ProcessingStatus.PENDING.value,
        storage_path="videos/1/sample.mp4",
    )
    sync_session.add(video)
    sync_session.commit()
    return video.id


def test_process_video_failure_marks_job_and_video_failed(sync_session, video_id):
    from app.tasks import video_tasks

    with (
        patch.object(video_tasks, "SyncSession", return_value=sync_session),
        patch.object(video_tasks, "run_audio_extraction", side_effect=RuntimeError("boom")),
        patch.object(video_tasks.process_video, "retry", side_effect=RuntimeError("retry_called")),
        pytest.raises(RuntimeError, match="retry_called"),
    ):
        task = video_tasks.process_video
        task.request.id = "fail-process-video"
        task(video_id)

    video = sync_session.get(Video, video_id)
    assert video is not None
    assert video.status == ProcessingStatus.FAILED.value
    assert "boom" in (video.error_message or "")

    job = sync_session.query(ProcessingJob).first()
    assert job is not None
    assert job.status == "failed"
    assert "boom" in (job.error_message or "")


def test_process_video_non_transient_validation_error_does_not_retry(sync_session, video_id):
    from app.services.video_acquisition import VideoValidationError
    from app.tasks import video_tasks

    with (
        patch.object(video_tasks, "SyncSession", return_value=sync_session),
        patch.object(
            video_tasks,
            "run_audio_extraction",
            side_effect=VideoValidationError("no audio track"),
        ),
        patch.object(video_tasks.process_video, "retry") as mock_retry,
        pytest.raises(VideoValidationError, match="no audio track"),
    ):
        task = video_tasks.process_video
        task.request.id = "fail-no-retry"
        task(video_id)

    mock_retry.assert_not_called()
    video = sync_session.get(Video, video_id)
    assert video is not None
    assert video.status == ProcessingStatus.FAILED.value
    assert "no audio track" in (video.error_message or "")

    job = sync_session.query(ProcessingJob).first()
    assert job is not None
    assert job.status == "failed"
    assert "no audio track" in (job.error_message or "")


def test_transcribe_audio_failure_sets_branch_failed(sync_session, video_id):
    from app.tasks import video_tasks

    job = ProcessingJob(
        video_id=video_id,
        task_id="branch-transcribe-fail",
        status="running",
        current_stage="parallel_processing",
        transcription_stage="queued",
        slides_stage="queued",
    )
    sync_session.add(job)
    sync_session.commit()
    job_id = job.id

    with (
        patch.object(video_tasks, "SyncSession", return_value=sync_session),
        patch.object(video_tasks, "run_transcription", side_effect=RuntimeError("transcribe-fail")),
        patch.object(
            video_tasks.transcribe_audio, "retry", side_effect=RuntimeError("retry_called")
        ),
        pytest.raises(RuntimeError, match="retry_called"),
    ):
        video_tasks.transcribe_audio(video_id)

    updated = sync_session.get(ProcessingJob, job_id)
    assert updated is not None
    assert updated.transcription_stage == "failed"


def test_extract_slides_failure_sets_branch_failed(sync_session, video_id):
    from app.tasks import video_tasks

    job = ProcessingJob(
        video_id=video_id,
        task_id="branch-slides-fail",
        status="running",
        current_stage="parallel_processing",
        transcription_stage="done",
        slides_stage="queued",
    )
    sync_session.add(job)
    sync_session.commit()
    job_id = job.id

    with (
        patch.object(video_tasks, "SyncSession", return_value=sync_session),
        patch.object(video_tasks, "run_slide_extraction", side_effect=RuntimeError("slides-fail")),
        patch.object(video_tasks.extract_slides, "retry", side_effect=RuntimeError("retry_called")),
        pytest.raises(RuntimeError, match="retry_called"),
    ):
        video_tasks.extract_slides(video_id)

    updated = sync_session.get(ProcessingJob, job_id)
    assert updated is not None
    assert updated.slides_stage == "failed"
