from __future__ import annotations

import dataclasses
import re

DEFAULT_K_VALUES: list[int] = [1, 3, 5, 10]

# pattern for characters not safe in a Qdrant collection name
_UNSAFE = re.compile(r"[^a-zA-Z0-9_]")


@dataclasses.dataclass(frozen=True)
class AblationConfig:
    name: str
    include_slide_text: bool
    include_context_template: bool
    embedding_model: str
    seed: int = 42

    def to_dict(self) -> dict[str, object]:
        return dataclasses.asdict(self)

    def collection_name(self) -> str:
        safe_name = _UNSAFE.sub("_", self.name)
        return f"eval_{safe_name}_{self.seed}"


@dataclasses.dataclass(frozen=True)
class AblationResult:
    config: AblationConfig
    retrieval_metrics: dict[str, float]
    segmentation_metrics: dict[str, float]
    query_type_breakdown: dict[str, dict[str, float]]
    timestamp: str

    def to_dict(self) -> dict[str, object]:
        return {
            "config": self.config.to_dict(),
            "retrieval_metrics": self.retrieval_metrics,
            "segmentation_metrics": self.segmentation_metrics,
            "query_type_breakdown": self.query_type_breakdown,
            "timestamp": self.timestamp,
        }


def get_standard_configs(seed: int = 42) -> list[AblationConfig]:
    return [
        AblationConfig(
            name="baseline",
            include_slide_text=False,
            include_context_template=False,
            embedding_model="bge-m3",
            seed=seed,
        ),
        AblationConfig(
            name="+OCR",
            include_slide_text=True,
            include_context_template=False,
            embedding_model="bge-m3",
            seed=seed,
        ),
        AblationConfig(
            name="+Context",
            include_slide_text=False,
            include_context_template=True,
            embedding_model="bge-m3",
            seed=seed,
        ),
        AblationConfig(
            name="+OCR+Context",
            include_slide_text=True,
            include_context_template=True,
            embedding_model="bge-m3",
            seed=seed,
        ),
        AblationConfig(
            name="+OCR+Context+Training",
            include_slide_text=True,
            include_context_template=True,
            embedding_model="bge-m3-finetuned",
            seed=seed,
        ),
    ]
