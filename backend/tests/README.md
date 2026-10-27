# Backend Tests

This directory contains the backend test suite for Seekr.

## Coverage Areas

- API behaviour
- authentication and ownership checks
- storage and upload flows
- slide extraction
- transcription
- retrieval and embedding logic
- database and migration behaviour
- integration coverage for service-backed flows

## Key Test Files

- `test_auth.py` - authentication rules and protected endpoint behaviour
- `test_videos.py` - video API behaviour, ownership scoping, and query routes
- `test_slide_extraction.py` - scene detection, OCR flow, deduplication, and slide clustering
- `test_transcription.py` - transcription service and CPU-safe behaviour
- `test_embedding.py` - embedding loading and retrieval-side model handling
- `test_jobs_api.py` - job polling, trigger, and cancellation flows
- `test_video_upload_integration.py` - end-to-end upload and storage integration
- `test_migrations_postgres.py` - migration correctness against PostgreSQL

## Common Commands

### Unit Tests

```bash
cd backend
../.venv/bin/pytest -q -m "not integration"
```

### Integration Tests

```bash
cd backend
../.venv/bin/pytest -q -m integration
```

### Type Checking

```bash
cd backend
../.venv/bin/mypy .
```

For the broader testing guide, see [`../../docs/testing.md`](../../docs/testing.md).
