from __future__ import annotations

import pytest
from app.evaluation.metrics.retrieval import hit_at_k, mean_hit_at_k, mean_mrr, mrr


class TestHitAtK:
    def test_hit_at_k_first_result_relevant(self) -> None:
        assert hit_at_k([1, 2, 3], {1, 2, 3}, 3) == 1.0

    def test_hit_at_k_relevant_not_in_top_k(self) -> None:
        # only [4, 5] checked at k=2; neither is in {1, 2, 3}
        assert hit_at_k([4, 5, 1], {1, 2, 3}, 2) == 0.0

    def test_hit_at_k_no_match(self) -> None:
        assert hit_at_k([4, 5, 6], {1, 2, 3}, 3) == 0.0

    def test_hit_at_k_relevant_at_boundary(self) -> None:
        # id 2 lands exactly at position k=2
        assert hit_at_k([4, 2], {1, 2}, 2) == 1.0

    def test_k_truncates_list(self) -> None:
        # only first 2 items checked; {4, 5} are not reached
        assert hit_at_k([1, 2, 3, 4, 5], {4, 5}, 2) == 0.0

    def test_empty_retrieved(self) -> None:
        assert hit_at_k([], {1, 2}, 5) == 0.0

    def test_empty_relevant(self) -> None:
        assert hit_at_k([1, 2, 3], set(), 3) == 0.0

    def test_k_zero(self) -> None:
        assert hit_at_k([1, 2], {1}, 0) == 0.0

    def test_duplicates_in_retrieved(self) -> None:
        # id 1 is relevant and appears at rank 1
        assert hit_at_k([1, 3, 3], {1, 2}, 3) == 1.0


class TestMRR:
    def test_first_hit_rank_1(self) -> None:
        assert mrr([1, 2, 3], {1}) == 1.0

    def test_first_hit_rank_3(self) -> None:
        assert mrr([4, 5, 1], {1}) == pytest.approx(1 / 3)

    def test_no_hit(self) -> None:
        assert mrr([4, 5, 6], {1}) == 0.0

    def test_multiple_relevant_returns_first(self) -> None:
        # 3 is not relevant; first relevant is 1 at rank 2 -> 1/2
        assert mrr([3, 1, 2], {1, 2}) == pytest.approx(0.5)

    def test_empty_retrieved(self) -> None:
        assert mrr([], {1}) == 0.0

    def test_empty_relevant(self) -> None:
        assert mrr([1, 2], set()) == 0.0


class TestMeanHitAtK:
    def test_average_of_two_queries(self) -> None:
        # first query hits (id 1 in top-3), second misses entirely -> mean 0.5
        results = [
            ([1, 2, 3], {1, 2, 3}),
            ([4, 5, 6], {1, 2, 3}),
        ]
        assert mean_hit_at_k(results, k=3) == pytest.approx(0.5)

    def test_empty_results_list(self) -> None:
        assert mean_hit_at_k([], k=5) == 0.0

    def test_single_query(self) -> None:
        results = [([1, 2], {1, 2, 3})]
        assert mean_hit_at_k(results, k=3) == pytest.approx(hit_at_k([1, 2], {1, 2, 3}, 3))


class TestMeanMRR:
    def test_average_of_two_queries(self) -> None:
        # first: hit at rank 1 (1.0), second: hit at rank 2 (0.5) → mean 0.75
        results = [
            ([1, 2, 3], {1}),
            ([4, 1, 3], {1}),
        ]
        assert mean_mrr(results) == pytest.approx(0.75)

    def test_empty_results_list(self) -> None:
        assert mean_mrr([]) == 0.0


class TestDeterminism:
    def test_same_input_same_output(self) -> None:
        retrieved = [3, 1, 4, 1, 5, 9]
        relevant = {1, 4}
        assert hit_at_k(retrieved, relevant, 4) == hit_at_k(retrieved, relevant, 4)
        assert mrr(retrieved, relevant) == mrr(retrieved, relevant)
