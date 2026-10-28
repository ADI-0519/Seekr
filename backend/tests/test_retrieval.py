from unittest.mock import patch

import pytest
from app.services.retrieval import RetrievalService, rrf_fuse


def chunk(id, text="some text", start=0.0, end=30.0, section_title=""):
    return {
        "id": id,
        "score": 1.0,
        "text": text,
        "start_time": start,
        "end_time": end,
        "position_category": "middle",
        "slide_text": "",
        "section_title": section_title,
    }


@pytest.fixture
def mock_backends():
    with (
        patch("app.services.retrieval.EmbeddingService") as emb,
        patch("app.services.retrieval.QdrantService") as qdrant,
    ):
        emb.return_value.embed_texts.return_value = [[0.1] * 1024]
        emb.return_value.bm25_encode.return_value = [{101: 1.0}]
        qdrant.return_value.search_chunks.return_value = []
        qdrant.return_value.search_chunks_sparse.return_value = []
        yield emb, qdrant


def test_rrf_doc_in_both_lists_ranks_higher():  # chunk 1 appears in both, chunk 2 only in dense
    dense = [chunk(1), chunk(2)]
    sparse = [chunk(1)]
    result = rrf_fuse(dense, sparse)
    assert result[0]["id"] == 1


def test_rrf_score_formula():
    k = 60
    result = rrf_fuse([chunk(1), chunk(2)], [chunk(1), chunk(2)], k=k)
    scores = {r["id"]: r["score"] for r in result}
    assert abs(scores[1] - 2 / (k + 1)) < 1e-9
    assert abs(scores[2] - 2 / (k + 2)) < 1e-9
    assert scores[1] > scores[2]


def test_rrf_scores_descending():
    dense = [chunk(i) for i in range(8)]
    sparse = [chunk(i) for i in range(4, 12)]
    result = rrf_fuse(dense, sparse)
    s = [r["score"] for r in result]
    assert s == sorted(s, reverse=True)


def test_rrf_empty_sparse():
    dense = [chunk(10), chunk(20), chunk(30)]
    result = rrf_fuse(dense, [])
    assert [r["id"] for r in result] == [10, 20, 30]


def test_rrf_both_empty():
    assert rrf_fuse([], []) == []


def test_rrf_attaches_score():
    result = rrf_fuse([chunk(1)], [])
    assert result[0]["score"] > 0


def test_empty_query_returns_nothing():
    svc = RetrievalService()
    assert svc.search(1, "") == []
    assert svc.search(1, "   ") == []


def test_no_results_from_qdrant(mock_backends):
    _, qdrant = mock_backends
    qdrant.return_value.search_chunks.return_value = []
    qdrant.return_value.search_chunks_sparse.return_value = []
    assert RetrievalService().search(1, "backpropagation") == []


def test_result_fields_populated(mock_backends):
    _, qdrant = mock_backends
    c = chunk(
        1, text="gradient descent explanation", start=12.0, end=42.0, section_title="Optimisation"
    )
    qdrant.return_value.search_chunks.return_value = [c]

    results = RetrievalService().search(video_id=1, query="gradient descent", top_k=1)

    assert len(results) == 1
    r = results[0]
    assert r["text"] == "gradient descent explanation"
    assert r["start_time"] == 12.0
    assert r["end_time"] == 42.0
    assert "score" in r
    assert r["segment_title"] == "Optimisation"


def test_top_k_respected(mock_backends):
    _, qdrant = mock_backends
    chunks = [chunk(i, text=f"text {i}", start=i * 30.0, end=(i + 1) * 30.0) for i in range(10)]
    qdrant.return_value.search_chunks.return_value = chunks

    assert len(RetrievalService().search(video_id=1, query="something", top_k=3)) == 3
    assert len(RetrievalService().search(video_id=1, query="something", top_k=1)) == 1


def test_both_search_paths_called(mock_backends):
    _, qdrant = mock_backends
    RetrievalService().search(video_id=5, query="neural networks")
    qdrant.return_value.search_chunks.assert_called_once()
    qdrant.return_value.search_chunks_sparse.assert_called_once()


def test_reranker_reorders_candidates(mock_backends):
    _, qdrant = mock_backends
    a = chunk(1, text="first")
    b = chunk(2, text="second")
    qdrant.return_value.search_chunks.return_value = [a, b]
    qdrant.return_value.search_chunks_sparse.return_value = []

    with patch("app.services.retrieval.RerankingService") as reranker:
        reranker.return_value.rerank.return_value = [b, a]
        results = RetrievalService().search(video_id=1, query="test", top_k=2)

    assert [r["text"] for r in results] == ["second", "first"]


def test_missing_section_title_is_none(mock_backends):
    _, qdrant = mock_backends
    chunk = {
        "id": 1,
        "score": 1.0,
        "text": "some content",
        "start_time": 0.0,
        "end_time": 30.0,
        "position_category": "beginning",
        "slide_text": "",
        # no section_title key
    }
    qdrant.return_value.search_chunks.return_value = [chunk]

    results = RetrievalService().search(video_id=1, query="content", top_k=1)
    assert results[0]["segment_title"] is None


def test_empty_section_title_is_none(mock_backends):
    _, qdrant = mock_backends
    qdrant.return_value.search_chunks.return_value = [chunk(1, section_title="")]

    results = RetrievalService().search(video_id=1, query="test", top_k=1)
    assert results[0]["segment_title"] is None
