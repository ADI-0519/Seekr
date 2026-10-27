from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "seekr",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.video_tasks", "app.tasks.retrieval_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="default",
    broker_heartbeat=0,
    broker_transport_options={"confirm_publish": True},
    task_routes={
        "app.tasks.video_tasks.extract_slides": {"queue": "slides"},
        "app.tasks.video_tasks.transcribe_audio": {"queue": "transcription"},
        "app.tasks.retrieval_tasks.query": {"queue": "retrieval"},
    },
)

celery_app.autodiscover_tasks(["app.tasks"])
