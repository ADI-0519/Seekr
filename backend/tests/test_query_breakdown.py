from __future__ import annotations

from typing import Literal

import pytest
from app.evaluation.metrics.breakdown import metrics_by_query_type
from app.evaluation.schemas import GroundTruthQuery

_QueryType = Literal["factual", "conceptual", "temporal", "slide-ref"]

_counter = 0


def make_query(
    query_id: str,
    query_type: _QueryType,
    video_id: int = 1,
    relevant_chunk_ids: list[int] | None = None,
) -> GroundTruthQuery:
    return GroundTruthQuery(
        query_id=query_id,
        query_text=f"question for {query_id}",
        query_type=query_type,
        video_id=video_id,
        relevant_chunk_ids=relevant_chunk_ids if relevant_chunk_ids is not None else [1],
        relevant_time_ranges=[(0.0, 30.0)],
    )


class TestMetricsByQueryType:
    def test_single_type_perfect_retrieval(self) -> None:
        queries = [
            make_query("q1", "factual", relevant_chunk_ids=[1, 2]),
            make_query("q2", "factual", relevant_chunk_ids=[1, 2]),
        ]
        result = metrics_by_query_type(
            queries,
            retrieval_fn=lambda text, vid: [1, 2, 3],
            k_values=[1, 2],
        )
        assert result["factual"]["hit@1"] == pytest.approx(1.0)
        assert result["factual"]["hit@2"] == pytest.approx(1.0)
        assert result["factual"]["mrr"] == pytest.approx(1.0)
        # only one type so _overall matches factual
        assert result["_overall"]["hit@1"] == pytest.approx(result["factual"]["hit@1"])
        assert result["_overall"]["mrr"] == pytest.approx(result["factual"]["mrr"])

    def test_two_types_different_performance(self) -> None:
        queries = [
            make_query("f1", "factual", video_id=1, relevant_chunk_ids=[1, 2]),
            make_query("f2", "factual", video_id=1, relevant_chunk_ids=[1, 2]),
            make_query("c1", "conceptual", video_id=2, relevant_chunk_ids=[10, 20]),
            make_query("c2", "conceptual", video_id=2, relevant_chunk_ids=[10, 20]),
        ]

        def retrieval_fn(text: str, vid: int) -> list[int]:
            return [1, 2, 3] if vid == 1 else [99]

        result = metrics_by_query_type(queries, retrieval_fn, k_values=[3])
        assert result["factual"]["hit@3"] == pytest.approx(1.0)
        assert result["conceptual"]["hit@3"] == pytest.approx(0.0)
        # mean across all 4 queries: (1.0 + 1.0 + 0.0 + 0.0) / 4
        assert result["_overall"]["hit@3"] == pytest.approx(0.5)

    def test_all_four_types_present(self) -> None:
        queries = [
            make_query("q1", "factual", relevant_chunk_ids=[1]),
            make_query("q2", "conceptual", relevant_chunk_ids=[1]),
            make_query("q3", "temporal", relevant_chunk_ids=[1]),
            make_query("q4", "slide-ref", relevant_chunk_ids=[1]),
        ]
        result = metrics_by_query_type(
            queries,
            retrieval_fn=lambda text, vid: [1],
            k_values=[1],
        )
        for key in ("factual", "conceptual", "temporal", "slide-ref", "_overall"):
            assert key in result
        for key in ("factual", "conceptual", "temporal", "slide-ref", "_overall"):
            assert result[key]["hit@1"] == pytest.approx(1.0)

    def test_custom_k_values(self) -> None:
        queries = [make_query("q1", "factual", relevant_chunk_ids=[1, 2, 3])]
        result = metrics_by_query_type(
            queries,
            retrieval_fn=lambda text, vid: [1],
            k_values=[1, 10, 50],
        )
        for key in ("hit@1", "hit@10", "hit@50", "mrr"):
            assert key in result["factual"]


class TestEdgeCases:
    def test_empty_queries(self) -> None:
        result = metrics_by_query_type([], retrieval_fn=lambda text, vid: [])
        assert set(result.keys()) == {"_overall"}
        expected = {"hit@1": 0.0, "hit@3": 0.0, "hit@5": 0.0, "hit@10": 0.0, "mrr": 0.0}
        assert result["_overall"] == expected

    def test_empty_k_values_raises(self) -> None:
        queries = [make_query("q1", "factual")]
        with pytest.raises(ValueError):
            metrics_by_query_type(queries, retrieval_fn=lambda text, vid: [1], k_values=[])

    def test_retrieval_fn_returns_empty(self) -> None:
        queries = [make_query("q1", "factual", relevant_chunk_ids=[1, 2])]
        result = metrics_by_query_type(
            queries,
            retrieval_fn=lambda text, vid: [],
            k_values=[1, 5],
        )
        assert result["factual"]["hit@1"] == pytest.approx(0.0)
        assert result["factual"]["hit@5"] == pytest.approx(0.0)
        assert result["factual"]["mrr"] == pytest.approx(0.0)


class TestDeterminism:
    def test_same_input_same_output(self) -> None:
        queries = [
            make_query("q1", "factual", relevant_chunk_ids=[1, 2]),
            make_query("q2", "conceptual", relevant_chunk_ids=[3]),
        ]
        fn = lambda text, vid: [1, 3, 5]  # noqa: E731
        r1 = metrics_by_query_type(queries, fn, k_values=[1, 5])
        r2 = metrics_by_query_type(queries, fn, k_values=[1, 5])
        assert r1 == r2
