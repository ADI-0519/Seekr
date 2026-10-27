import os
import sys
import types
from pathlib import Path

import pytest
from app.core.celery_app import celery_app
from app.core.config import get_settings


@pytest.fixture(autouse=True)
def celery_eager():
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield
    celery_app.conf.task_always_eager = False
    celery_app.conf.task_eager_propagates = False


@pytest.fixture
def alembic_sqlite_env(tmp_path: Path):
    old = os.environ.get(
        "ALEMBIC_DATABASE_URL"
    )  # save whatever was there before so we don't mess up other tests/dev env

    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    os.environ["ALEMBIC_DATABASE_URL"] = db_url

    try:
        yield db_url
    finally:
        os.environ.pop(
            "ALEMBIC_DATABASE_URL", None
        )  # stop sqlite leaking into the postgres migration test, (ts is miserable to debug)

        if old is not None:
            os.environ["ALEMBIC_DATABASE_URL"] = old


def load_root_env() -> None:
    root_env = Path(__file__).resolve().parents[2] / ".env"
    if not root_env.exists():
        return

    for raw_line in root_env.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip()


@pytest.fixture(autouse=True)
def integration_env(request):
    if request.node.get_closest_marker("integration") is None:
        yield
        return

    load_root_env()
    previous = dict(os.environ)

    endpoint = os.getenv("STORAGE_ENDPOINT_URL")
    if endpoint and "minio:9000" in endpoint:
        os.environ["STORAGE_ENDPOINT_URL"] = endpoint.replace("minio:9000", "localhost:9000")

    # Keep S3 credentials aligned with the MinIO root credentials used by docker compose.
    minio_user = os.getenv("MINIO_ROOT_USER")
    minio_pass = os.getenv("MINIO_ROOT_PASSWORD")
    if minio_user and minio_pass:
        os.environ["STORAGE_ACCESS_KEY_ID"] = minio_user
        os.environ["STORAGE_SECRET_ACCESS_KEY"] = minio_pass

    get_settings.cache_clear()
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(previous)
        get_settings.cache_clear()


@pytest.fixture(autouse=True)
def ensure_faster_whisper_module():
    if "faster_whisper" in sys.modules:
        yield
        return

    stub = types.ModuleType("faster_whisper")

    class WhisperModel:  # pragma: no cover - used only when dependency is absent in test env
        def __init__(self, *args, **kwargs):
            pass

    stub.WhisperModel = WhisperModel
    sys.modules["faster_whisper"] = stub
    try:
        yield
    finally:
        sys.modules.pop("faster_whisper", None)
