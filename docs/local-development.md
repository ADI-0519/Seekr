# Local Development

## Prerequisites

- Docker Desktop
- Node.js 20+
- Python 3.11
- npm

## Environment Files

Seekr uses two main environment files locally:

- root `.env` for backend containers
- `frontend/.env` for the web application

## Root `.env`

Create `.env` at the repository root with values appropriate for your local setup.
The example below uses local development defaults only; do not reuse these credentials in deployed environments.

Example:

```env
POSTGRES_DB=SeekrDB
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/SeekrDB

REDIS_URL=redis://redis:6379/0

RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672//
CELERY_BROKER_URL=amqp://guest:guest@rabbitmq:5672//
CELERY_RESULT_BACKEND=redis://redis:6379/1

QDRANT_URL=http://qdrant:6333

MINIO_ROOT_USER=minio_local
MINIO_ROOT_PASSWORD=minio_local_password
STORAGE_ENDPOINT_URL=http://minio:9000
STORAGE_BUCKET=seekr-videos
STORAGE_ACCESS_KEY_ID=minio_local
STORAGE_SECRET_ACCESS_KEY=minio_local_password

ALLOWED_ORIGINS=http://localhost:8081,http://localhost:3000
```

These values are suitable for local development only.

## Frontend `.env`

Create `frontend/.env` with:

```env
EXPO_PUBLIC_API_URL=http://localhost:8000
EXPO_PUBLIC_FIREBASE_API_KEY=...
EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN=...
EXPO_PUBLIC_FIREBASE_PROJECT_ID=...
EXPO_PUBLIC_FIREBASE_APP_ID=...
```

For testing from a phone on the same network, replace `localhost` with your machine IP.

## Start The Backend

From `backend/`:

```bash
python scripts/start.py cpu --build --setup-models
```

That first-run command builds the images and initializes the shared model cache. Normal CPU starts are simply:

```bash
python scripts/start.py
```

For NVIDIA GPU workers, use:

```bash
python scripts/start.py gpu
```

The base `docker-compose.yml` is the complete CPU stack. `docker-compose.gpu.yml` only overrides the four ML workers with CUDA images and GPU access. Compose creates and retains the database, object-storage, and model-cache volumes automatically.

## Start The Frontend

From `frontend/`:

```bash
npm ci
npx expo start --web
```

## Verify The Stack

1. Open `http://localhost:8000/health` and confirm the API returns a healthy response.
2. Open `http://localhost:8081` and confirm the frontend loads.
3. Upload a lecture and watch the processing state update in the UI.

## Local Service URLs

- API: `http://localhost:8000`
- Frontend: `http://localhost:8081`
- MinIO console: `http://localhost:9001`
- RabbitMQ management: `http://localhost:15672`
- Qdrant: `http://localhost:6333`
