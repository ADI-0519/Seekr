from unittest.mock import MagicMock, patch

import app.services.reranker as reranker_mod
import pytest
from app.services.reranker import RerankingService


def candidate(id, text="some text", score=0.5):
    return {
        "id": id,
        "text": text,
        "start_time": float(id * 30),
        "end_time": float(id * 30 + 30),
        "score": score,
        "section_title": "",
        "slide_text": "",
        "position_category": "middle",
    }


@pytest.fixture(autouse=True)
def reset_model():
    reranker_mod._model = None
    reranker_mod._load_attempted = False
    yield
    reranker_mod._model = None
    reranker_mod._load_attempted = False


def make_mock_model(scores):
    m = MagicMock()
    m.predict.return_value = scores
    return m


def test_rerank_sorted_by_score_not_input_order():
    # input order: [A, B, C] but cross-encoder prefers C > A > B
    candidates = [candidate(0), candidate(1), candidate(2)]
    mock_model = make_mock_model([0.4, 0.1, 0.9])

    with patch.object(reranker_mod, "get_model", return_value=mock_model):
        results = RerankingService().rerank("query", candidates, top_k=3)

    ids = [r["id"] for r in results]
    assert ids == [2, 0, 1]


def test_top_k_truncation():
    candidates = [candidate(i) for i in range(6)]
    mock_model = make_mock_model([0.1, 0.9, 0.3, 0.8, 0.2, 0.5])

    with patch.object(reranker_mod, "get_model", return_value=mock_model):
        results = RerankingService().rerank("query", candidates, top_k=3)

    assert len(results) == 3


def test_score_is_overwritten_with_reranker_score():
    candidates = [candidate(0, score=999.0), candidate(1, score=999.0)]
    mock_model = make_mock_model([0.7, 0.3])

    with patch.object(reranker_mod, "get_model", return_value=mock_model):
        results = RerankingService().rerank("query", candidates, top_k=2)

    assert abs(results[0]["score"] - 0.7) < 1e-6
    assert abs(results[1]["score"] - 0.3) < 1e-6


def test_model_load_failure_returns_candidates_unchanged():
    candidates = [candidate(0), candidate(1), candidate(2)]

    with patch.object(reranker_mod, "get_model", return_value=None):
        results = RerankingService().rerank("query", candidates, top_k=2)

    assert len(results) == 2
    assert results[0]["id"] == 0
    assert results[1]["id"] == 1


def test_inference_failure_falls_back_gracefully():
    candidates = [candidate(i) for i in range(3)]
    mock_model = make_mock_model(None)
    mock_model.predict.side_effect = RuntimeError("CUDA OOM")

    with patch.object(reranker_mod, "get_model", return_value=mock_model):
        results = RerankingService().rerank("query", candidates, top_k=2)

    # should still return top_k, just in RRF order
    assert len(results) == 2


def test_empty_candidates_returns_empty():
    with patch.object(reranker_mod, "get_model", return_value=make_mock_model([])):
        results = RerankingService().rerank("query", [], top_k=5)
    assert results == []


def test_top_k_larger_than_candidates():
    candidates = [candidate(0), candidate(1)]
    mock_model = make_mock_model([0.8, 0.2])

    with patch.object(reranker_mod, "get_model", return_value=mock_model):
        results = RerankingService().rerank("query", candidates, top_k=10)

    assert len(results) == 2


def test_original_fields_preserved():
    c = candidate(42, text="backprop explained")
    mock_model = make_mock_model([0.95])

    with patch.object(reranker_mod, "get_model", return_value=mock_model):
        results = RerankingService().rerank("backprop", [c], top_k=1)

    assert results[0]["text"] == "backprop explained"
    assert results[0]["id"] == 42
    assert results[0]["start_time"] == 42 * 30
