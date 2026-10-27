# Seekr

Seekr turns lecture recordings into searchable, structured study material. Upload a video or paste a YouTube link and get back a timestamped transcript, topic-segmented notes, slide extraction with OCR, semantic search, and grounded Q&A.

- Deployed app: <https://www.seek-r.me/>
- Fine-tuned retrieval model: ClearML ID `acaa0613f7d14064916002872e25d5d4`

## Live demo

- Web app: [seek-r.me](https://www.seek-r.me/)
- Documentation index: [`docs/README.md`](docs/README.md)

## What it does

- lecture upload (file or YouTube URL) with background processing
- timestamped transcription via faster-whisper
- slide extraction with scene detection and EasyOCR
- topic segmentation with GPT-5-nano-generated titles and GPT-5-mini summaries
- hybrid retrieval (BGE-M3 dense + BM25 sparse + RRF + cross-encoder reranking)
- grounded Q&A with timestamp citations
- PDF notes export
- user accounts with Firebase Auth

## Quick start

### Backend

Copy the example env file and fill in your OpenAI key — that is the only value you need to set for local development:

```bash
cp .env.example .env
# edit .env and set OPENAI_API_KEY
```

Then start the stack:

```bash
cd backend
bash scripts/start.sh
```

`start.sh` cleans the HF cache, builds Docker images, downloads BGE-M3 and EasyOCR models, optionally exports the fine-tuned embedding checkpoint from ClearML, then brings the stack up. First run takes a few minutes for the model downloads.

```bash
bash scripts/start.sh cpu   # force CPU mode
bash scripts/start.sh gpu   # force GPU mode
```

### Frontend

In a separate terminal:

```bash
cd frontend
npm ci
npx expo start --web
```

- Frontend: `http://localhost:8081`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

Full environment setup, `.env` values, and Docker notes are in [`docs/local-development.md`](docs/local-development.md).

## Project structure

```
Seekr/
├── backend/
│   ├── app/
│   │   ├── api/            API routes
│   │   ├── tasks/          Celery task orchestration
│   │   ├── services/       transcription, segmentation, retrieval, OCR, QA, exports
│   │   ├── finetune/       synthetic query generation, triplet building, BGE-M3 training
│   │   ├── evaluation/     retrieval and segmentation evaluation with ablation support
│   │   ├── models/         SQLAlchemy models
│   │   └── crud/           database access layer
│   ├── alembic/            database migrations
│   ├── scripts/            startup helpers and experiment runners
│   └── tests/              unit and integration tests
├── frontend/               Expo Router / React Native Web
├── docs/                   architecture, API, deployment, testing docs
└── scripts/                repo-level helpers
```

## Evaluation

The evaluation pipeline measures retrieval and segmentation quality across five ablation configurations. It reports Hit@K, MRR, and Seg-F1, broken down by query type (factual, conceptual, temporal, slide-ref).

### Artifacts

The pipeline needs a sentences export and the retrieval gold fixtures, which are not committed to the repo. Download them first:

```bash
cd backend
python scripts/download_artifacts.py --eval
```

Requires `gdown` (`pip install gdown --break-system-packages`).

### Running evaluation

```bash
cd backend

# standard run
python scripts/run_evaluation.py

# evaluate a specific fine-tuned model from ClearML
python scripts/run_evaluation.py --finetune-task-id acaa0613f7d14064916002872e25d5d4

# dispatch to ClearML A100 agent
python scripts/run_evaluation.py --remote --clearml-task-name evaluation-final
```

`run_evaluation.py` accepts the following flags:

| Flag | Default | Description |
|------|---------|-------------|
| `--output-dir` | `evaluation_output/results` | where to write `results.json`, `report.md`, and plots |
| `--finetune-task-id` | none | ClearML task ID of a fine-tuned model to load as `+OCR+Context+Training` |
| `--clearml-task-name` | `evaluation` | ClearML experiment name |
| `--remote` | off | enqueue on a ClearML agent instead of running locally |
| `--sentences-json` | `evaluation_output/sentences.json` | override path to the transcript export |
| `--gold-retrieval` | `app/evaluation/fixtures/retrieval_gold.json` | override retrieval ground-truth path |

For finer control — choosing specific ablations, K values, or doing a dry run — call the module directly:

```bash
# dry run — validates fixtures and config, no services needed
python -m app.evaluation --dry-run

# run a subset of ablations with custom K values
python -m app.evaluation \
  --ablations "baseline,+OCR,+OCR+Context,+OCR+Context+Training" \
  --k-values "1,3,5,10" \
  --output-dir evaluation_output/results \
  --seed 42
```

### Output files

Results are written to `--output-dir`:

| File | Description |
|------|-------------|
| `results.json` | full machine-readable results for every ablation config |
| `report.md` | Hit@K, MRR, and Seg-F1 table across configs |
| `plots/recall_comparison.png` | grouped bar chart of Hit@K per config |
| `plots/delta_over_baseline.png` | improvement over baseline per config |

For the fixture format, how to add ground-truth queries, and metrics definitions, see [`backend/app/evaluation/README.md`](backend/app/evaluation/README.md).

## Fine-tuning

The fine-tuning pipeline generates synthetic queries from lecture transcripts using GPT-5-mini, builds structure-aware hard-negative triplets, and trains BGE-M3 with contrastive loss (InfoNCE). The trained checkpoint is what the `+OCR+Context+Training` ablation loads.

### Artifacts

Prebuilt training data (chunks and triplets exported from the full dataset) is available via:

```bash
cd backend
python scripts/download_artifacts.py --finetune
```

This downloads to `runs/finetune/data/` and is used by default.

### Running fine-tuning

```bash
cd backend

# train locally using prebuilt data
python scripts/run_finetune_pipeline.py --output-dir runs/finetune/model_v4

# dispatch to ClearML A100 agent and wait for completion
python scripts/run_finetune_pipeline.py \
  --output-dir runs/finetune/model_v4 \
  --remote-train

# rebuild training data from the DB for specific lectures, then train
python scripts/run_finetune_pipeline.py \
  --no-prebuilt-data \
  --video-ids 132,133,134 \
  --output-dir runs/finetune/model_v4
```

When `--remote-train` is set, the script dispatches to ClearML, polls for completion, and prints the task ID. Pass that to `run_evaluation.py --finetune-task-id` to evaluate.

### Fine-tuning flags

| Flag | Default | Description |
|------|---------|-------------|
| `--output-dir` | `runs/finetune/model_v4` | where to write checkpoints and `run_manifest.json` |
| `--no-prebuilt-data` | off | rebuild training data from the DB (requires `--video-ids` and `DATABASE_URL`) |
| `--video-ids` | none | comma-separated lecture IDs to export |
| `--base-model` | local BGE-M3 or `BAAI/bge-m3` | base model path or HuggingFace ID |
| `--epochs` | `3` | training epochs |
| `--batch-size` | `16` | per-GPU batch size |
| `--grad-accum` | `1` | gradient accumulation steps |
| `--lr` | `2e-5` | learning rate |
| `--warmup-ratio` | `0.06` | warmup fraction |
| `--seed` | `42` | random seed |
| `--hard-frac` | `0.4` | fraction of hard negatives per batch |
| `--medium-frac` | `0.3` | fraction of medium negatives per batch |
| `--mining-hard-frac` | `0.4` | hard negative fraction during online mining |
| `--mining-medium-frac` | `0.3` | medium negative fraction during online mining |
| `--similarity-threshold` | `0.45` | cosine threshold for deduplicating near-duplicate negatives |
| `--clearml-task-name` | `finetune-bge-m3` | ClearML experiment name |
| `--remote-train` | off | dispatch training to a ClearML agent |
| `--quality-strictness` | `medium` | synthetic query filter (`low`, `medium`, `high`) — only applies when `--no-prebuilt-data` is set |
| `--check-ratio` | `0.13` | fraction of lectures held out for validation |
| `--force-export` | off | re-export chunks from DB even if `chunks.jsonl` exists |

After a run, `--output-dir` contains `best/` and `final/` checkpoints and a `run_manifest.json` with the full config, git state, and triplet counts.

## Reproducing the reported results

```bash
cd backend

# download all artifacts
python scripts/download_artifacts.py --finetune --eval

# evaluate the submitted fine-tuned model against all ablation configs
python scripts/run_evaluation.py \
  --finetune-task-id acaa0613f7d14064916002872e25d5d4 \
  --output-dir evaluation_output/results_final
```

Results will be at `evaluation_output/results_final/report.md`.

## Testing

```bash
cd backend

# unit tests — no services needed
../.venv/bin/pytest -q -m "not integration"

# integration tests — requires the Docker stack
../.venv/bin/pytest -q -m integration

# type checking
../.venv/bin/mypy .
```

See [`docs/testing.md`](docs/testing.md) for the full test strategy and coverage setup.

## Tech stack

**Frontend:** Expo Router, React Native Web, TypeScript, Zustand, React Query, Firebase Auth

**Backend:** FastAPI, Celery, SQLAlchemy, Alembic, Pydantic v2

**ML:** faster-whisper (large-v3-turbo), BGE-M3, BM25Plus, ms-marco-MiniLM-L-6-v2 (reranker), EasyOCR, PySceneDetect, GPT-5-nano (segmentation titles), GPT-5-mini (summaries, Q&A, synthetic query generation)

**Infrastructure:** PostgreSQL, Qdrant, RabbitMQ, Redis, MinIO, Docker Compose, ClearML

(Note: in the event of YouTube url submission not working in deployment, they will still work on localhost/ ; Keats/Kaltura links will always work)