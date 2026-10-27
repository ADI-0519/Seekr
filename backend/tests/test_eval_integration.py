from __future__ import annotations

import os
import random
import string
from unittest.mock import MagicMock

import pytest
from app.evaluation.ablation import AblationConfig, AblationResult
from app.evaluation.runner import EvaluationRunner
from app.evaluation.schemas import GroundTruthQuery
from app.services.chunking import ChunkingService

pytestmark = pytest.mark.integration


def random_suffix() -> str:
    return "".join(random.choices(string.ascii_lowercase, k=6))


def make_query(
    query_id: str,
    video_id: int = 1,
    relevant_chunk_ids: list[int] | None = None,
) -> GroundTruthQuery:
    # runner uses video_id * 100_000 + chunk_index, so [100000, 100001] hits the first two chunks
    ids = relevant_chunk_ids if relevant_chunk_ids is not None else [100000, 100001]
    return GroundTruthQuery(
        query_id=query_id,
        query_text=f"What is discussed in chunk {query_id}?",
        query_type="factual",
        video_id=video_id,
        relevant_chunk_ids=ids,
        relevant_time_ranges=[[0.0, 30.0]],
    )


def make_sentences(count: int = 10, duration: float = 300.0) -> list[dict[str, object]]:
    step = duration / count
    return [
        {
            "text": f"Test sentence number {i} about a topic.",
            "start_time": round(i * step, 2),
            "end_time": round((i + 1) * step, 2),
        }
        for i in range(count)
    ]


def mock_embed_svc(vector_size: int = 1024) -> MagicMock:
    mock = MagicMock()
    rng = random.Random(42)

    def fake_embed(texts: list[str]) -> list[list[float]]:
        return [[rng.random() for _ in range(vector_size)] for _ in texts]

    mock.embed_texts.side_effect = fake_embed
    mock.bm25_encode.side_effect = lambda texts: [{"word": 1.0}] * len(texts)
    return mock


@pytest.fixture
def qdrant_svc():  # type: ignore[no-untyped-def]
    if not os.environ.get("QDRANT_URL"):
        pytest.skip("QDRANT_URL not set")
    from app.services.qdrant_client import QdrantService

    svc = QdrantService()
    try:
        svc.client.get_collections()
    except Exception:
        pytest.skip("qdrant not reachable")
    yield svc


def test_runner_produces_valid_metrics(qdrant_svc) -> None:  # type: ignore[no-untyped-def]
    queries = [make_query(f"q_{i:03d}") for i in range(5)]
    sentences = make_sentences(count=10, duration=300.0)
    embed_svc = mock_embed_svc()
    chunking_svc = ChunkingService()

    runner = EvaluationRunner(chunking_svc, embed_svc, qdrant_svc)
    config = AblationConfig(
        name=f"test_valid_{random_suffix()}",
        include_slide_text=False,
        include_context_template=False,
        embedding_model="bge-m3",
        seed=42,
    )

    result = runner.run_ablation(
        config,
        queries,
        sentences,
        video_duration=300.0,
        k_values=[1, 3, 5, 10],
    )

    assert isinstance(result, AblationResult)
    assert isinstance(result.timestamp, str)
    assert len(result.timestamp) > 0
    for val in result.retrieval_metrics.values():
        assert isinstance(val, float)
        assert 0.0 <= val <= 1.0


def test_temp_collection_cleaned_up(qdrant_svc) -> None:  # type: ignore[no-untyped-def]
    queries = [make_query("q_cleanup")]
    sentences = make_sentences(count=5, duration=150.0)
    embed_svc = mock_embed_svc()
    chunking_svc = ChunkingService()

    runner = EvaluationRunner(chunking_svc, embed_svc, qdrant_svc)
    original_collection = qdrant_svc.collection
    config = AblationConfig(
        name=f"test_cleanup_{random_suffix()}",
        include_slide_text=False,
        include_context_template=False,
        embedding_model="bge-m3",
        seed=42,
    )

    runner.run_ablation(config, queries, sentences, video_duration=150.0)

    # temp collection must be gone
    collections = qdrant_svc.client.get_collections().collections
    names = {c.name for c in collections}
    assert config.collection_name() not in names

    # original collection name must be restored on the service
    assert qdrant_svc.collection == original_collection


def test_runner_zero_hits_graceful(qdrant_svc) -> None:  # type: ignore[no-untyped-def]
    # relevant IDs that cannot match any upserted chunk (runner uses video_id * 100_000 + i)
    queries = [make_query("q_miss", relevant_chunk_ids=[999999])]
    sentences = make_sentences(count=5, duration=150.0)
    embed_svc = mock_embed_svc()
    chunking_svc = ChunkingService()

    runner = EvaluationRunner(chunking_svc, embed_svc, qdrant_svc)
    config = AblationConfig(
        name=f"test_zero_{random_suffix()}",
        include_slide_text=False,
        include_context_template=False,
        embedding_model="bge-m3",
        seed=42,
    )

    result = runner.run_ablation(config, queries, sentences, video_duration=150.0)

    overall = result.retrieval_metrics
    assert overall.get("hit@1", 1.0) == 0.0
    assert overall.get("hit@3", 1.0) == 0.0
    assert overall.get("mrr", 1.0) == 0.0
