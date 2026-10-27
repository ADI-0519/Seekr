from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class RetrievalMetrics:
    hit_at_1: float
    hit_at_5: float
    hit_at_10: float
    mrr: float


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return float(sum(x * y for x, y in zip(a, b, strict=False)))


def _ranked_doc_indices(
    query_vec: Sequence[float], doc_vecs: Sequence[Sequence[float]]
) -> list[int]:
    scores = [(_dot(query_vec, dv), i) for i, dv in enumerate(doc_vecs)]
    scores.sort(key=lambda t: t[0], reverse=True)
    return [i for _, i in scores]


def evaluate_retrieval(
    *,
    query_embeddings: Sequence[Sequence[float]],
    doc_embeddings: Sequence[Sequence[float]],
    positive_doc_indices: Sequence[int],
) -> RetrievalMetrics:
    if len(query_embeddings) != len(positive_doc_indices):
        raise ValueError("positive_doc_indices must match number of queries")
    n = len(query_embeddings)
    if n == 0:
        raise ValueError("Must provide at least one query")

    q = np.array(query_embeddings, dtype=np.float32)
    d = np.array(doc_embeddings, dtype=np.float32)
    scores = q @ d.T

    pos = np.array(positive_doc_indices)
    ranked = np.argsort(-scores, axis=1)

    hits_1 = int(np.sum(ranked[:, 0] == pos))
    hits_5 = int(np.sum(np.any(ranked[:, :5] == pos[:, None], axis=1)))
    hits_10 = int(np.sum(np.any(ranked[:, :10] == pos[:, None], axis=1)))

    ranks = np.where(ranked == pos[:, None])[1] + 1
    rr_sum = float(np.sum(1.0 / ranks))

    return RetrievalMetrics(
        hit_at_1=hits_1 / n,
        hit_at_5=hits_5 / n,
        hit_at_10=hits_10 / n,
        mrr=rr_sum / n,
    )
