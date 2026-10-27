from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path

import pytest
from app.evaluation.data_loader import (
    get_default_retrieval_path,
    get_default_segmentation_path,
    load_retrieval_gold,
    load_segmentation_gold,
)
from app.evaluation.schemas import GroundTruthQuery, SegmentationGoldLabel
from pydantic import ValidationError

# minimal valid payloads reused across tests

_VALID_QUERY: dict[str, object] = {
    "query_id": "q_001",
    "query_text": "What is the learning rate?",
    "query_type": "factual",
    "video_id": 1,
    "relevant_chunk_ids": [1001, 1002],
    "relevant_time_ranges": [[60.0, 90.0]],
    "expected_segment_id": None,
}

_VALID_LABEL: dict[str, object] = {
    "video_id": 1,
    "expected_boundaries": [300.0, 900.0, 1800.0],
    "tolerance_secs": 15.0,
}

_fixtures_available = pytest.mark.skipif(
    not get_default_retrieval_path().exists(),
    reason="gold fixtures not downloaded -- run: python scripts/download_artifacts.py --eval",
)


class TestGroundTruthQuery:
    def test_valid_query_round_trip(self) -> None:
        query = GroundTruthQuery.model_validate(_VALID_QUERY)
        dumped = query.model_dump()
        reparsed = GroundTruthQuery.model_validate(dumped)
        assert reparsed.query_id == query.query_id
        assert reparsed.query_text == query.query_text
        assert reparsed.query_type == query.query_type
        assert reparsed.video_id == query.video_id
        assert reparsed.relevant_chunk_ids == query.relevant_chunk_ids
        assert reparsed.relevant_time_ranges == query.relevant_time_ranges
        assert reparsed.expected_segment_id == query.expected_segment_id

    def test_empty_relevant_chunk_ids_rejected(self) -> None:
        payload = {**_VALID_QUERY, "relevant_chunk_ids": []}
        with pytest.raises((ValueError, ValidationError)):
            GroundTruthQuery.model_validate(payload)

    def test_invalid_time_range_rejected(self) -> None:
        # start > end
        payload = {**_VALID_QUERY, "relevant_time_ranges": [[90.0, 60.0]]}
        with pytest.raises((ValueError, ValidationError)):
            GroundTruthQuery.model_validate(payload)

    def test_time_range_equal_start_end_rejected(self) -> None:
        # start == end is also invalid
        payload = {**_VALID_QUERY, "relevant_time_ranges": [[60.0, 60.0]]}
        with pytest.raises((ValueError, ValidationError)):
            GroundTruthQuery.model_validate(payload)

    def test_invalid_query_type_rejected(self) -> None:
        payload = {**_VALID_QUERY, "query_type": "invalid"}
        with pytest.raises((ValueError, ValidationError)):
            GroundTruthQuery.model_validate(payload)

    def test_missing_query_text_rejected(self) -> None:
        payload = {k: v for k, v in _VALID_QUERY.items() if k != "query_text"}
        with pytest.raises((ValueError, ValidationError)):
            GroundTruthQuery.model_validate(payload)


class TestSegmentationGoldLabel:
    def test_valid_label_round_trip(self) -> None:
        label = SegmentationGoldLabel.model_validate(_VALID_LABEL)
        dumped = label.model_dump()
        reparsed = SegmentationGoldLabel.model_validate(dumped)
        assert reparsed.video_id == label.video_id
        assert reparsed.expected_boundaries == label.expected_boundaries
        assert reparsed.tolerance_secs == label.tolerance_secs

    def test_unsorted_boundaries_rejected(self) -> None:
        payload = {**_VALID_LABEL, "expected_boundaries": [300.0, 100.0, 600.0]}
        with pytest.raises((ValueError, ValidationError)):
            SegmentationGoldLabel.model_validate(payload)

    def test_negative_tolerance_rejected(self) -> None:
        payload = {**_VALID_LABEL, "tolerance_secs": -1.0}
        with pytest.raises((ValueError, ValidationError)):
            SegmentationGoldLabel.model_validate(payload)

    def test_zero_tolerance_rejected(self) -> None:
        payload = {**_VALID_LABEL, "tolerance_secs": 0.0}
        with pytest.raises((ValueError, ValidationError)):
            SegmentationGoldLabel.model_validate(payload)

    def test_empty_boundaries_accepted(self) -> None:
        # a video with no topic shifts is a valid edge case
        payload = {**_VALID_LABEL, "expected_boundaries": []}
        label = SegmentationGoldLabel.model_validate(payload)
        assert label.expected_boundaries == []


class TestDataLoader:
    @_fixtures_available
    def test_load_retrieval_gold_from_fixtures(self) -> None:
        queries = load_retrieval_gold(get_default_retrieval_path())
        assert len(queries) > 0
        assert all(isinstance(q, GroundTruthQuery) for q in queries)

    @_fixtures_available
    def test_load_segmentation_gold_from_fixtures(self) -> None:
        labels = load_segmentation_gold(get_default_segmentation_path())
        assert len(labels) >= 1
        assert all(isinstance(label, SegmentationGoldLabel) for label in labels)

    def test_load_retrieval_duplicate_query_id_rejected(self, tmp_path: Path) -> None:
        entries = [
            {**_VALID_QUERY, "query_id": "q_dup"},
            {**_VALID_QUERY, "query_id": "q_dup"},
        ]
        fixture = tmp_path / "retrieval.json"
        fixture.write_text(json.dumps(entries), encoding="utf-8")
        with pytest.raises(ValueError, match="Duplicate query_id"):
            load_retrieval_gold(fixture)

    def test_load_segmentation_duplicate_video_id_rejected(self, tmp_path: Path) -> None:
        entries = [
            {**_VALID_LABEL, "video_id": 99},
            {**_VALID_LABEL, "video_id": 99},
        ]
        fixture = tmp_path / "segmentation.json"
        fixture.write_text(json.dumps(entries), encoding="utf-8")
        with pytest.raises(ValueError, match="Duplicate video_id"):
            load_segmentation_gold(fixture)

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_retrieval_gold(tmp_path / "nonexistent.json")

    def test_load_malformed_json_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{this is not valid json", encoding="utf-8")
        with pytest.raises(JSONDecodeError):
            load_retrieval_gold(bad)
