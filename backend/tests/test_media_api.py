from __future__ import annotations

from app.api.media import get_storage, router
from app.core.firebase_auth import get_authenticated_user
from app.db.session import get_db
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeBody:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    def iter_chunks(self):
        for chunk in self._chunks:
            yield chunk


class _FakeStorage:
    def __init__(self, response=None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.last_key: str | None = None
        self.last_range: str | None = None

    def sanitize_key(self, key: str) -> str:
        return key

    def get_object_stream(self, key: str, range_header: str | None = None):
        self.last_key = key
        self.last_range = range_header
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


class _FakeResult:
    def __init__(self, owned: bool) -> None:
        self.owned = owned

    def scalar_one_or_none(self):
        return 1 if self.owned else None


class _FakeDb:
    def __init__(self, owned: bool) -> None:
        self.owned = owned

    async def execute(self, _statement):
        return _FakeResult(self.owned)


def _build_client(
    *,
    auth_user: dict | None,
    storage: _FakeStorage,
    owned: bool = True,
) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api")

    async def _override_auth():
        return auth_user

    def _override_storage():
        return storage

    async def _override_db():
        yield _FakeDb(owned)

    app.dependency_overrides[get_authenticated_user] = _override_auth
    app.dependency_overrides[get_storage] = _override_storage
    app.dependency_overrides[get_db] = _override_db
    return TestClient(app)


def test_proxy_media_rejects_unauthorized_requests():
    storage = _FakeStorage(
        response=(_FakeBody([b"ignored"]), "video/mp4", 7, None),
    )
    client = _build_client(auth_user=None, storage=storage)

    response = client.get("/api/media/videos/1/example.mp4")

    assert response.status_code == 401
    assert storage.last_key is None


def test_proxy_media_returns_404_when_storage_raises():
    storage = _FakeStorage(error=FileNotFoundError("missing"))
    client = _build_client(auth_user={"uid": "u1"}, storage=storage)

    response = client.get("/api/media/videos/1/missing.mp4")

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"
    assert storage.last_key == "videos/1/missing.mp4"


def test_proxy_media_rejects_storage_key_not_owned_by_authenticated_user():
    storage = _FakeStorage(
        response=(_FakeBody([b"private"]), "video/mp4", 7, None),
    )
    client = _build_client(auth_user={"uid": "u1"}, storage=storage, owned=False)

    response = client.get("/api/media/videos/2/private.mp4")

    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"
    assert storage.last_key is None


def test_proxy_media_streams_full_content_with_headers():
    storage = _FakeStorage(
        response=(_FakeBody([b"hello", b"world"]), "video/mp4", 10, None),
    )
    client = _build_client(auth_user={"uid": "u1"}, storage=storage)

    response = client.get("/api/media/videos/7/chunk.mp4")

    assert response.status_code == 200
    assert response.content == b"helloworld"
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["cache-control"] == "private, max-age=3600"
    assert response.headers["content-length"] == "10"
    assert "content-range" not in response.headers
    assert storage.last_key == "videos/7/chunk.mp4"
    assert storage.last_range is None


def test_proxy_media_supports_range_requests():
    storage = _FakeStorage(
        response=(
            _FakeBody([b"data"]),
            "video/mp4",
            4,
            "bytes 0-3/100",
        ),
    )
    client = _build_client(auth_user={"uid": "u1"}, storage=storage)

    response = client.get("/api/media/videos/2/range.mp4", headers={"Range": "bytes=0-3"})

    assert response.status_code == 206
    assert response.headers["content-range"] == "bytes 0-3/100"
    assert response.headers["content-length"] == "4"
    assert storage.last_range == "bytes=0-3"
