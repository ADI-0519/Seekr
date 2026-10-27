from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

from app.evaluation.metrics.retrieval import hit_at_k, mrr
from app.evaluation.schemas import GroundTruthQuery

_DEFAULT_K_VALUES = [1, 3, 5, 10]


def _zero_metrics(k_values: list[int]) -> dict[str, float]:
    metrics: dict[str, float] = {f"hit@{k}": 0.0 for k in k_values}
    metrics["mrr"] = 0.0
    return metrics


def _compute_group_metrics(
    queries: list[GroundTruthQuery],
    retrieved_map: dict[str, list[int]],
    k_values: list[int],
) -> dict[str, float]:
    accum: dict[str, float] = {f"hit@{k}": 0.0 for k in k_values}
    accum["mrr"] = 0.0
    n = len(queries)
    for query in queries:
        retrieved = retrieved_map[query.query_id]
        relevant = set(query.relevant_chunk_ids)
        for k in k_values:
            accum[f"hit@{k}"] += hit_at_k(retrieved, relevant, k)
        accum["mrr"] += mrr(retrieved, relevant)
    return {key: val / n for key, val in accum.items()}


def metrics_by_query_type(
    queries: list[GroundTruthQuery],
    retrieval_fn: Callable[[str, int], list[int]],
    k_values: list[int] | None = None,
) -> dict[str, dict[str, float]]:
    resolved_k = k_values if k_values is not None else _DEFAULT_K_VALUES

    if k_values is not None and len(k_values) == 0:
        raise ValueError("k_values must not be empty")

    if not queries:
        return {"_overall": _zero_metrics(resolved_k)}

    # call retrieval_fn once per query and cache results by query_id
    retrieved_map: dict[str, list[int]] = {
        q.query_id: retrieval_fn(q.query_text, q.video_id) for q in queries
    }

    groups: dict[str, list[GroundTruthQuery]] = defaultdict(list)
    for query in queries:
        groups[query.query_type].append(query)

    result: dict[str, dict[str, float]] = {}

    for query_type, group_queries in groups.items():
        if not group_queries:
            continue
        result[query_type] = _compute_group_metrics(group_queries, retrieved_map, resolved_k)

    result["_overall"] = _compute_group_metrics(queries, retrieved_map, resolved_k)

    return result
