# Backend

The backend is responsible for API delivery, job orchestration, storage integration, and the lecture-processing pipeline.

## Responsibilities

- serve the FastAPI application
- accept uploads and create processing jobs
- coordinate Celery task flows
- store metadata in PostgreSQL
- store media assets in object storage
- index searchable content in Qdrant

## Main Components

- `app/api/` - API routes
- `app/tasks/` - Celery task orchestration
- `app/services/` - business logic, storage, OCR, transcription, retrieval, and exports
- `app/models/` - SQLAlchemy models
- `alembic/` - database migrations
- `scripts/` - startup helpers and local runtime utilities
- `docker-compose*.yml` - local runtime definitions

## Local Run

From `backend/`:

### CPU (default)

```bash
python scripts/start.py
```

The first run should build the images and initialize the model cache:

```bash
python scripts/start.py cpu --build --setup-models
```

### GPU

```bash
python scripts/start.py gpu --build --setup-models
```

Normal starts reuse existing images and model caches. Add `--build` after code or dependency changes, and use `--setup-models` only when the model cache needs initializing or refreshing.

For lower-level Docker commands and environment setup, see [`../docs/local-development.md`](../docs/local-development.md).

## Useful Endpoints

- `GET /health` - service health
- `GET /api/` - lecture listing
- `POST /api/upload` - upload a lecture file
- `GET /api/{video_id}/status` - processing status
- `POST /api/{video_id}/query` - lecture search and grounded Q&A

## Backend Checks

```bash
../.venv/bin/pytest -q -m "not integration"
../.venv/bin/mypy .
```

For more detail, see:

- [`../docs/local-development.md`](../docs/local-development.md)
- [`../docs/testing.md`](../docs/testing.md)
- [`../docs/architecture.md`](../docs/architecture.md)

## Evaluation Pipeline

The project includes a reproducible evaluation pipeline for measuring retrieval and segmentation quality. It supports ablation experiments to isolate the contribution of OCR, context templates, and embedding configurations.

### Quick Start

```bash
# validate config without running (no services needed)
python -m app.evaluation --dry-run

# full evaluation run
python -m app.evaluation --output-dir evaluation_output/

# run with specific ablations
python -m app.evaluation --ablations "baseline,+OCR" --k-values "1,3,5,10" --seed 42
```

### Documentation

See [`app/evaluation/README.md`](app/evaluation/README.md) for the complete CLI reference, guide on adding ground-truth queries, and metrics documentation.
