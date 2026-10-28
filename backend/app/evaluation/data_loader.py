from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from app.evaluation.schemas import GroundTruthQuery, SegmentationGoldLabel

log = logging.getLogger(__name__)

# -1 flags chunk IDs that aren't known at annotation time, runner resolves them via time-range overlap
_SENTINEL_CHUNK_ID = -1


def load_retrieval_gold(path: str | Path) -> list[GroundTruthQuery]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    try:
        queries = [GroundTruthQuery.model_validate(item) for item in raw]
    except ValidationError as exc:
        raise ValueError(f"Invalid retrieval benchmark data in {path}: {exc}") from exc

    ids = [q.query_id for q in queries]
    duplicates = {qid for qid in ids if ids.count(qid) > 1}
    if duplicates:
        raise ValueError(f"Duplicate query_id values found: {sorted(duplicates)}")

    return queries


def load_segmentation_gold(path: str | Path) -> list[SegmentationGoldLabel]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    try:
        labels = [SegmentationGoldLabel.model_validate(item) for item in raw]
    except ValidationError as exc:
        raise ValueError(f"Invalid segmentation benchmark data in {path}: {exc}") from exc

    video_ids = [label.video_id for label in labels]
    duplicates = {vid for vid in video_ids if video_ids.count(vid) > 1}
    if duplicates:
        raise ValueError(f"Duplicate video_id values found: {sorted(duplicates)}")

    return labels


def get_default_retrieval_path() -> Path:
    return Path(__file__).parent / "fixtures" / "retrieval_gold.json"


def get_default_segmentation_path() -> Path:
    return Path(__file__).parent / "fixtures" / "segmentation_gold.json"
