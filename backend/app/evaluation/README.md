# Retrieval Quality Benchmark

This module runs Seekr's reproducible retrieval quality benchmark, including topic-segmentation measurements. It supports ablation comparisons across four indexing configurations — `baseline`, `+OCR`, `+Context`, and `+OCR+Context` — and produces a markdown report table, a machine-readable JSON file, and comparison plots showing Hit@K and per-config deltas over baseline.

## Benchmark Data and ClearML

The benchmark uses transcript text, retrieval queries, expected time ranges, and topic-boundary labels. Remote runs upload this benchmark data and, when selected, fine-tuned model artifacts to ClearML. Only synthetic, licensed, or explicitly approved anonymised data may be used. Do not use real user lecture content unless its transfer to ClearML is covered by the applicable consent, privacy policy, and data-processing agreement.

Run `python scripts/validate_benchmark_data.py` after downloading the benchmark data. The validator blocks common university names, module codes, student identifiers, academic email addresses, and coursework-specific terms. This automated check supplements—not replaces—manual review for names or other identifying context.

## Quick Start

```bash
# dry run — validates fixture loading and config, no services needed
python -m app.evaluation --dry-run

# full run — requires Qdrant and the embedding service
python -m app.evaluation --output-dir evaluation_output/
```

## Prerequisites

- **Qdrant** running locally (via `docker-compose` or standalone)
- **Python deps**: `pip install -r requirements_dev.txt`
- **matplotlib** (optional) — required only for plot generation; the JSON and markdown report work without it

## CLI Reference

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--gold-retrieval` | PATH | downloaded benchmark data | Path to retrieval benchmark JSON |
| `--gold-segmentation` | PATH | downloaded benchmark data | Path to segmentation benchmark JSON |
| `--output-dir` | PATH | `evaluation_output` | Directory to write all output files |
| `--ablations` | TEXT | `baseline,+OCR,+Context,+OCR+Context` | Comma-separated ablation names to run |
| `--k-values` | TEXT | `1,3,5,10` | Comma-separated K values for Recall@K |
| `--seed` | INT | `42` | Random seed for reproducibility |
| `--dry-run` | flag | off | Load fixtures and print parsed config only — skips service instantiation and ablation runs |

Valid `--ablations` values are the names defined in `get_standard_configs()`: `baseline`, `+OCR`, `+Context`, `+OCR+Context`. Unknown names are skipped with a warning.

## Output Files

All files are written to `--output-dir`:

| File | Description |
|------|-------------|
| `results.json` | Full machine-readable results for every ablation config |
| `report.md` | Markdown table comparing Recall@K, MRR, and Seg-F1 across configs |
| `plots/recall_comparison.png` | Grouped bar chart of Recall@K per config |
| `plots/delta_over_baseline.png` | Horizontal bar chart of metric improvement over the baseline config |

## Adding Retrieval Benchmark Queries

1. Open `app/evaluation/fixtures/retrieval_gold.json`.
2. Append a new entry following the `GroundTruthQuery` schema:

```json
{
  "query_id": "q_017",
  "query_text": "What activation function was used in the output layer?",
  "query_type": "factual",
  "video_id": 1,
  "relevant_chunk_ids": [1055, 1056],
  "relevant_time_ranges": [[820.0, 875.0]],
  "expected_segment_id": 5
}
```

3. Valid `query_type` values: `"factual"`, `"conceptual"`, `"temporal"`, `"slide-ref"`.
4. `relevant_chunk_ids` must reference real Qdrant point IDs from a processed video. `expected_segment_id` is optional.
5. Each `query_id` must be unique. Each entry in `relevant_time_ranges` must have `start < end`.
6. Validate the fixture loads cleanly:

```bash
python -m app.evaluation --dry-run
```

## Adding Segmentation Benchmark Labels

1. Open `app/evaluation/fixtures/segmentation_gold.json`.
2. Append a new entry following the `SegmentationGoldLabel` schema:

```json
{
  "video_id": 4,
  "expected_boundaries": [300.0, 720.0, 1150.0],
  "tolerance_secs": 15.0
}
```

3. `expected_boundaries` must be sorted in ascending order. Each `video_id` must be unique. `tolerance_secs` must be greater than 0 (default: `15.0`).

## Adding a New Ablation Config

1. Open `app/evaluation/ablation.py`.
2. Add a new entry to the list returned by `get_standard_configs()`:

```python
AblationConfig(
    name="+BM25Only",
    include_slide_text=False,
    include_context_template=False,
    embedding_model="bge-m3",
    seed=seed,
),
```

3. The `name` must match what you pass via `--ablations`:

```bash
python -m app.evaluation --ablations "baseline,+BM25Only"
```

## Metrics Reference

**Recall@K** — fraction of relevant chunk IDs that appear in the top-K retrieved results, averaged across all queries. Higher is better; K=1 is the strictest.

**MRR (Mean Reciprocal Rank)** — for each query, the reciprocal of the rank of the first relevant result; averaged across queries. A score of 1.0 means every query's top result was relevant.

**Segmentation F1** — compares predicted topic-boundary timestamps against expected benchmark boundaries using a greedy match within a configurable `tolerance_secs` window (default 15 s). Precision = matched / predicted; Recall = matched / expected; F1 = harmonic mean.

**Query-type breakdown** — all three retrieval metrics (Recall@K for each K, MRR) computed separately for each `query_type` (`factual`, `conceptual`, `temporal`, `slide-ref`) and for `_overall`. Useful for diagnosing which query categories drive score differences.

## Interpreting Results

The report table shows one row per ablation config:

```
| Config        | Recall@1   | Recall@3   | Recall@5   | Recall@10  | MRR        | Seg-F1     |
|---------------|------------|------------|------------|------------|------------|------------|
| baseline      | 0.6500     | 0.7800     | 0.8500     | 0.9200     | 0.7200     | 0.0000     |
| +OCR          | 0.7000     | 0.8200     | 0.8800     | 0.9400     | 0.7600     | 0.0000     |
```

- A `Recall@1` above ~0.65 indicates the top result is relevant for most queries.
- Compare rows to identify which ablation flag (`+OCR`, `+Context`, or both) contributes most.
- `delta_over_baseline.png` shows the same comparison visually: bars to the right of zero are improvements; bars to the left are regressions.
- `Seg-F1` is `0.0000` until segmentation evaluation is wired into the runner (currently returns `{}`).
- The **first config** in the results list is always treated as the baseline for the delta chart.

## Running Tests

```bash
# unit tests only — no services needed
pytest tests/test_eval_schemas.py tests/test_retrieval_metrics.py tests/test_segmentation_metrics.py tests/test_query_breakdown.py tests/test_ablation_runner.py tests/test_eval_report.py -v

# integration tests — requires Qdrant
pytest tests/test_eval_integration.py -v -m integration
```
