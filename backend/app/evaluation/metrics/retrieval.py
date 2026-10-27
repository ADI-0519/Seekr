from __future__ import annotations


# hit@k not set-recall: dividing by |relevant| breaks when a time range maps to multiple chunks
def hit_at_k(retrieved_ids: list[int], relevant_ids: set[int], k: int) -> float:
    if not relevant_ids or k <= 0 or not retrieved_ids:
        return 0.0
    return 1.0 if any(rid in relevant_ids for rid in retrieved_ids[:k]) else 0.0


def mrr(retrieved_ids: list[int], relevant_ids: set[int]) -> float:
    if not retrieved_ids or not relevant_ids:
        return 0.0
    for rank, rid in enumerate(retrieved_ids, start=1):
        if rid in relevant_ids:
            return 1.0 / rank
    return 0.0


def mean_hit_at_k(results: list[tuple[list[int], set[int]]], k: int) -> float:
    if not results:
        return 0.0
    return sum(hit_at_k(r, rel, k) for r, rel in results) / len(results)


def mean_mrr(results: list[tuple[list[int], set[int]]]) -> float:
    if not results:
        return 0.0
    return sum(mrr(r, rel) for r, rel in results) / len(results)
