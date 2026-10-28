# Seekr

Seekr turns lecture recordings into searchable, structured study material. Upload a video or paste a YouTube link and get back a timestamped transcript, topic-segmented notes, slide extraction with OCR, semantic search, and grounded Q&A.

## Documentation

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

Seekr includes a reproducible evaluation pipeline for retrieval and topic segmentation. It compares dense, sparse, OCR-aware, context-aware, and fine-tuned configurations using Hit@K, MRR, and Seg-F1, with retrieval results broken down by factual, conceptual, temporal, and slide-reference queries.

The original benchmark datasets and result artifacts are not included in this repository. The evaluation framework, metric implementations, report generation, fixtures format, and extension guide are documented in [`backend/app/evaluation/README.md`](backend/app/evaluation/README.md).

## Fine-tuning

The training pipeline generates synthetic queries from lecture transcripts, builds structure-aware hard-negative triplets, and fine-tunes BGE-M3 with contrastive loss. It supports local execution and ClearML orchestration, records the run configuration and git state, and produces separate best and final checkpoints. See [`backend/scripts/run_finetune_pipeline.py`](backend/scripts/run_finetune_pipeline.py) for the available options.

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

(Note: in the event of YouTube URL submission not working in deployment, links will still work on localhost; Kaltura links will always work.)
