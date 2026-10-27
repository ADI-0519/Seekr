from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class GroundTruthQuery(BaseModel):
    query_id: str
    query_text: str
    query_type: Literal["factual", "conceptual", "temporal", "slide-ref", "section"]
    video_id: int
    relevant_chunk_ids: list[int]
    relevant_time_ranges: list[tuple[float, float]]
    expected_segment_id: int | None = None

    @field_validator("relevant_chunk_ids")
    @classmethod
    def check_chunk_ids_non_empty(cls, v: list[int]) -> list[int]:
        if len(v) < 1:
            raise ValueError("relevant_chunk_ids must contain at least one element")
        return v

    @field_validator("relevant_time_ranges")
    @classmethod
    def check_time_ranges(cls, v: list[tuple[float, float]]) -> list[tuple[float, float]]:
        for start, end in v:
            if start >= end:
                raise ValueError(f"Each time range must have start < end, got ({start}, {end})")
        return v


class SegmentationGoldLabel(BaseModel):
    video_id: int
    expected_boundaries: list[float]
    tolerance_secs: float = Field(15.0, gt=0)

    @field_validator("expected_boundaries")
    @classmethod
    def check_boundaries_sorted(cls, v: list[float]) -> list[float]:
        if v != sorted(v):
            raise ValueError("expected_boundaries must be sorted in ascending order")
        return v
