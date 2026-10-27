from app.core.celery_app import celery_app
from app.tasks.video_tasks import (
    create_embeddings,
    extract_audio,
    extract_slides,
    finish_pipeline,
    process_video,
    segment_transcript,
    transcribe_audio,
)


def test_process_video_config():
    assert process_video.name == "app.tasks.video_tasks.process_video"
    assert process_video.max_retries == 2


def test_all_tasks_registered():
    tasks = [
        extract_audio,
        transcribe_audio,
        extract_slides,
        segment_transcript,
        create_embeddings,
        finish_pipeline,
    ]
    for t in tasks:
        assert t.name.startswith("app.tasks.video_tasks.")


def test_process_video_signature():
    sig = process_video.s(video_id=1)
    assert sig.kwargs == {"video_id": 1}


def test_extract_audio_signature():
    sig = extract_audio.s(1, "/tmp/vid.mp4")
    assert sig.args == (1, "/tmp/vid.mp4")


def test_extract_slides_routes_to_slides_queue():
    routes = celery_app.conf.task_routes or {}
    slide_route = routes.get("app.tasks.video_tasks.extract_slides", {})
    assert slide_route.get("queue") == "slides"


def test_transcribe_audio_routes_to_transcription_queue():
    routes = celery_app.conf.task_routes or {}
    transcription_route = routes.get("app.tasks.video_tasks.transcribe_audio", {})
    assert transcription_route.get("queue") == "transcription"


def test_finish_pipeline_registered():
    assert finish_pipeline.name == "app.tasks.video_tasks.finish_pipeline"
