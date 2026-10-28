from unittest.mock import MagicMock, patch

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
    with patch("app.services.storage.StorageService") as MockStorage:
        storage_instance = MockStorage.return_value
        storage_instance.generate_object_key.return_value = "video/1/sample.mp4"

        v = Video(
            id=1,
            title="Test Lecture",
            status=ProcessingStatus.PENDING.value,
            storage_path="video/1/sample.mp4",
        )
        sync_session.add(v)
        sync_session.commit()
        return v.id


def test_process_video_runs_audio_and_dispatches_chord(sync_session, video_id):
    from app.tasks import video_tasks

    mock_chord = MagicMock()

    with (
        patch.object(video_tasks, "SyncSession", return_value=sync_session),
        patch.object(video_tasks, "run_audio_extraction", return_value="audio/1/audio.wav"),
        patch.object(video_tasks, "run_transcription"),
        patch.object(video_tasks, "run_slide_extraction"),
        patch.object(video_tasks, "run_embedding"),
        patch.object(video_tasks, "chord", mock_chord),
    ):
        task = video_tasks.process_video
        task.request.id = "test-celery-id"
        result = task(video_id)

    assert result["status"] == "running"
    assert result["stage"] == "parallel_dispatched"
    mock_chord.assert_called_once()

    job = sync_session.query(ProcessingJob).first()
    assert job is not None
    assert job.task_id == "test-celery-id"
    assert job.transcription_stage == "queued"
    assert job.slides_stage == "queued"


def test_process_video_sets_audio_stage(sync_session, video_id):
    from app.tasks import video_tasks

    stages_seen = []
    original_update = video_tasks.update_job

    def spy_update(session, job_id, **fields):
        if "current_stage" in fields:
            stages_seen.append(fields["current_stage"])
        return original_update(session, job_id, **fields)

    with (
        patch.object(video_tasks, "SyncSession", return_value=sync_session),
        patch.object(video_tasks, "run_audio_extraction", return_value="audio/1/audio.wav"),
        patch.object(video_tasks, "run_transcription"),
        patch.object(video_tasks, "run_slide_extraction"),
        patch.object(video_tasks, "run_embedding"),
        patch.object(video_tasks, "update_job", side_effect=spy_update),
        patch.object(video_tasks, "chord", MagicMock()),
    ):
        task = video_tasks.process_video
        task.request.id = "test-stages"
        task(video_id)

    assert ProcessingStatus.EXTRACTING_AUDIO.value in stages_seen
    assert "parallel_processing" in stages_seen


def test_video_status_updated_on_failure(sync_session, video_id):
    from app.tasks import video_tasks

    with (
        patch.object(video_tasks, "SyncSession", return_value=sync_session),
        patch.object(video_tasks, "run_audio_extraction", side_effect=RuntimeError("GPU exploded")),
        patch.object(video_tasks.process_video, "max_retries", 0),
        pytest.raises(Exception),
    ):
        task = video_tasks.process_video
        task.request.id = "test-fail"
        task(video_id)

    video = sync_session.get(Video, video_id)
    assert video.status == ProcessingStatus.FAILED.value

    job = sync_session.query(ProcessingJob).first()
    assert job.status == "failed"
    assert "GPU exploded" in job.error_message


def test_transcribe_audio_updates_branch_status(sync_session, video_id):
    from app.tasks import video_tasks

    job = ProcessingJob(
        video_id=video_id,
        task_id="test-branch",
        status="running",
        current_stage="parallel_processing",
        transcription_stage="queued",
        slides_stage="queued",
    )
    sync_session.add(job)
    sync_session.commit()

    with (
        patch.object(video_tasks, "SyncSession", return_value=sync_session),
        patch.object(video_tasks, "run_transcription"),
        patch.object(sync_session, "close"),
    ):
        result = video_tasks.transcribe_audio(video_id)

    assert result["branch"] == "transcription"
    assert result["status"] == "done"

    sync_session.refresh(job)
    assert job.transcription_stage == "done"


def test_extract_slides_updates_branch_status(sync_session, video_id):
    from app.tasks import video_tasks

    job = ProcessingJob(
        video_id=video_id,
        task_id="test-branch",
        status="running",
        current_stage="parallel_processing",
        transcription_stage="queued",
        slides_stage="queued",
    )
    sync_session.add(job)
    sync_session.commit()

    with (
        patch.object(video_tasks, "SyncSession", return_value=sync_session),
        patch.object(video_tasks, "run_slide_extraction", return_value=5),
        patch.object(sync_session, "close"),
    ):
        result = video_tasks.extract_slides(video_id)

    assert result["branch"] == "slides"
    assert result["status"] == "done"
    assert result["frame_count"] == 5

    sync_session.refresh(job)
    assert job.slides_stage == "done"


def test_finish_pipeline_completes_job(sync_session, video_id):
    from app.tasks import video_tasks

    job = ProcessingJob(
        video_id=video_id,
        task_id="test-finish",
        status="running",
        current_stage="parallel_processing",
        transcription_stage="done",
        slides_stage="done",
    )
    sync_session.add(job)
    sync_session.commit()

    with (
        patch.object(video_tasks, "SyncSession", return_value=sync_session),
        patch.object(video_tasks, "run_segmentation", return_value=3),
        patch.object(video_tasks, "run_embedding"),
        patch.object(video_tasks.time, "sleep"),
        patch.object(sync_session, "close"),
    ):
        result = video_tasks.finish_pipeline(video_id)

    assert result["status"] == "done"
    sync_session.refresh(job)
    assert job.status == "done"
    assert job.current_stage == ProcessingStatus.COMPLETE.value
    assert job.completed_at is not None

    video = sync_session.get(Video, video_id)
    assert video.status == ProcessingStatus.COMPLETE.value
