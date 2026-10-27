from __future__ import annotations

import pytest
from app.evaluation.metrics.segmentation import mean_segmentation_f1, segmentation_f1


class TestSegmentationF1:
    def test_perfect_match(self) -> None:
        result = segmentation_f1([300.0, 600.0], [300.0, 600.0])
        assert result["precision"] == pytest.approx(1.0)
        assert result["recall"] == pytest.approx(1.0)
        assert result["f1"] == pytest.approx(1.0)

    def test_within_tolerance(self) -> None:
        # predicted is 10s off, well within default 15s tolerance
        result = segmentation_f1([310.0], [300.0], tolerance_secs=15.0)
        assert result["precision"] == pytest.approx(1.0)
        assert result["recall"] == pytest.approx(1.0)
        assert result["f1"] == pytest.approx(1.0)

    def test_outside_tolerance(self) -> None:
        result = segmentation_f1([320.0], [300.0], tolerance_secs=15.0)
        assert result["precision"] == pytest.approx(0.0)
        assert result["recall"] == pytest.approx(0.0)
        assert result["f1"] == pytest.approx(0.0)

    def test_exact_tolerance_boundary_matches(self) -> None:
        # distance == tolerance_secs should match (<=)
        result = segmentation_f1([315.0], [300.0], tolerance_secs=15.0)
        assert result["recall"] == pytest.approx(1.0)

    def test_partial_match(self) -> None:
        # 2 predicted, 2 gold, only 1 match
        result = segmentation_f1([300.0, 999.0], [300.0, 600.0])
        assert result["precision"] == pytest.approx(0.5)
        assert result["recall"] == pytest.approx(0.5)

    def test_both_empty(self) -> None:
        result = segmentation_f1([], [])
        assert result == {"precision": 1.0, "recall": 1.0, "f1": 1.0}

    def test_predicted_empty_gold_nonempty(self) -> None:
        result = segmentation_f1([], [300.0, 600.0])
        assert result["precision"] == pytest.approx(1.0)
        assert result["recall"] == pytest.approx(0.0)
        assert result["f1"] == pytest.approx(0.0)

    def test_gold_empty_predicted_nonempty(self) -> None:
        result = segmentation_f1([300.0, 600.0], [])
        assert result["precision"] == pytest.approx(0.0)
        assert result["recall"] == pytest.approx(1.0)
        assert result["f1"] == pytest.approx(0.0)

    def test_greedy_closest_match(self) -> None:
        # two predicted boundaries near one gold; closest (305) should win, leaving 295 unmatched
        result = segmentation_f1([295.0, 305.0], [300.0], tolerance_secs=15.0)
        assert result["precision"] == pytest.approx(0.5)
        assert result["recall"] == pytest.approx(1.0)

    def test_gold_not_reused(self) -> None:
        # both predictions are near the same gold; only one can match
        result = segmentation_f1([300.0, 301.0], [300.0], tolerance_secs=15.0)
        assert result["precision"] == pytest.approx(0.5)
        assert result["recall"] == pytest.approx(1.0)

    def test_negative_tolerance_raises(self) -> None:
        with pytest.raises(ValueError):
            segmentation_f1([300.0], [300.0], tolerance_secs=-1.0)

    def test_zero_tolerance_raises(self) -> None:
        with pytest.raises(ValueError):
            segmentation_f1([300.0], [300.0], tolerance_secs=0.0)

    def test_f1_formula(self) -> None:
        # 2 predicted, 4 gold, 1 match → precision=0.5, recall=0.25
        result = segmentation_f1([300.0, 999.0], [300.0, 600.0, 900.0, 1200.0])
        assert result["precision"] == pytest.approx(0.5)
        assert result["recall"] == pytest.approx(0.25)
        expected_f1 = 2 * 0.5 * 0.25 / (0.5 + 0.25)
        assert result["f1"] == pytest.approx(expected_f1)


class TestMeanSegmentationF1:
    def test_average_of_two(self) -> None:
        results = [
            {"precision": 1.0, "recall": 1.0, "f1": 1.0},
            {"precision": 0.0, "recall": 0.0, "f1": 0.0},
        ]
        mean = mean_segmentation_f1(results)
        assert mean["precision"] == pytest.approx(0.5)
        assert mean["recall"] == pytest.approx(0.5)
        assert mean["f1"] == pytest.approx(0.5)

    def test_empty_list(self) -> None:
        assert mean_segmentation_f1([]) == {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    def test_single_entry_passthrough(self) -> None:
        entry = {"precision": 0.8, "recall": 0.6, "f1": 0.686}
        result = mean_segmentation_f1([entry])
        assert result["precision"] == pytest.approx(0.8)
        assert result["recall"] == pytest.approx(0.6)
        assert result["f1"] == pytest.approx(0.686)
