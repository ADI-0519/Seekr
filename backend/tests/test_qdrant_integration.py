import os
import random
import string

import pytest
from app.services.qdrant_client import QdrantService


def random_suffix():
    return "".join(random.choices(string.ascii_lowercase, k=6))


def make_chunk(chunk_id, video_id, text="test text", start=0.0, end=30.0, pos="beginning"):
    return {
        "id": chunk_id,
        "vector": [0.1] * 1024,
        "sparse_vector": {101: 1.0, 202: 0.8},
        "payload": {
            "video_id": video_id,
            "text": text,
            "start_time": start,
            "end_time": end,
            "position_category": pos,
            "slide_text": "",
            "section_title": "",
        },
    }


@pytest.fixture
def qdrant_service():
    if not os.environ.get("QDRANT_URL"):
        pytest.skip("qdrant not available")

    collection = f"test_lecture_chunks_{random_suffix()}"
    svc = QdrantService()
    svc.collection = collection
    try:
        svc.ensure_collection_with_sparse()
    except Exception:
        pytest.skip("qdrant not reachable")

    yield svc

    svc.client.delete_collection(collection)


def test_upsert_and_search_by_video_id(qdrant_service):
    svc = qdrant_service

    chunks_v1 = [make_chunk(1000 + i, video_id=1) for i in range(5)]
    chunks_v2 = [make_chunk(2000 + i, video_id=2) for i in range(3)]
    svc.upsert_chunks(chunks_v1 + chunks_v2)

    query = [random.random() for _ in range(1024)]
    results = svc.search_chunks(video_id=1, query_vector=query, top_k=10)

    assert len(results) <= 5
    for r in results:
        assert r["id"] in range(1000, 1005)


def test_search_returns_correct_fields(qdrant_service):
    svc = qdrant_service

    chunk = {
        "id": 9999,
        "vector": [0.5] * 1024,
        "sparse_vector": {303: 2.1, 404: 1.8},
        "payload": {
            "video_id": 42,
            "text": "backpropagation computes gradients",
            "start_time": 30.0,
            "end_time": 60.0,
            "position_category": "middle",
            "slide_text": "Chain Rule",
            "section_title": "Optimisation",
        },
    }
    svc.upsert_chunks([chunk])

    results = svc.search_chunks(video_id=42, query_vector=[0.5] * 1024, top_k=1)

    assert len(results) == 1
    r = results[0]
    assert r["text"] == "backpropagation computes gradients"
    assert r["start_time"] == 30.0
    assert r["end_time"] == 60.0
    assert r["position_category"] == "middle"
    assert r["slide_text"] == "Chain Rule"
    assert r["section_title"] == "Optimisation"


def test_upsert_idempotent(qdrant_service):
    svc = qdrant_service
    chunk = make_chunk(5555, video_id=7)

    svc.upsert_chunks([chunk])
    svc.upsert_chunks([chunk])

    info = svc.client.get_collection(svc.collection)
    assert info.points_count == 1


def test_empty_collection_search(qdrant_service):
    svc = qdrant_service
    query = [random.random() for _ in range(1024)]
    results = svc.search_chunks(video_id=99, query_vector=query, top_k=5)
    assert results == []


def test_search_top_k_limit(qdrant_service):
    svc = qdrant_service
    chunks = [make_chunk(3000 + i, video_id=5) for i in range(10)]
    svc.upsert_chunks(chunks)

    query = [random.random() for _ in range(1024)]
    results = svc.search_chunks(video_id=5, query_vector=query, top_k=3)

    assert len(results) == 3
