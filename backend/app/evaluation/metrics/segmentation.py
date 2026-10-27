from __future__ import annotations


def segmentation_f1(
    predicted_boundaries: list[float],
    gold_boundaries: list[float],
    tolerance_secs: float = 15.0,
) -> dict[str, float]:
    if tolerance_secs <= 0:
        raise ValueError(f"tolerance_secs must be positive, got {tolerance_secs}")

    # vacuously correct when both lists are empty
    if not predicted_boundaries and not gold_boundaries:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}

    if not predicted_boundaries:
        return {"precision": 1.0, "recall": 0.0, "f1": 0.0}

    if not gold_boundaries:
        return {"precision": 0.0, "recall": 1.0, "f1": 0.0}

    matched: set[int] = set()
    true_positives = 0

    for pred in predicted_boundaries:
        # find the closest unmatched gold boundary within tolerance
        best_idx: int | None = None
        best_dist = float("inf")
        for idx, gold in enumerate(gold_boundaries):
            if idx in matched:
                continue
            dist = abs(pred - gold)
            if dist <= tolerance_secs and dist < best_dist:
                best_dist = dist
                best_idx = idx
        if best_idx is not None:
            matched.add(best_idx)
            true_positives += 1

    precision = true_positives / len(predicted_boundaries)
    recall = true_positives / len(gold_boundaries)
    denom = precision + recall
    f1 = 2.0 * precision * recall / denom if denom > 0.0 else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def mean_segmentation_f1(results: list[dict[str, float]]) -> dict[str, float]:
    if not results:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    n = len(results)
    return {
        "precision": sum(r["precision"] for r in results) / n,
        "recall": sum(r["recall"] for r in results) / n,
        "f1": sum(r["f1"] for r in results) / n,
    }
