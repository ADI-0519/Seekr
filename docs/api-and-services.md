# API And Services

This document is a high-level reference for local service ports and the main API routes used by the Seekr frontend.

## Local Service Ports

| Port | Service |
| --- | --- |
| `8000` | FastAPI backend |
| `5432` | PostgreSQL |
| `6379` | Redis |
| `5672` | RabbitMQ |
| `6333` | Qdrant API |
| `6334` | Qdrant gRPC |
| `9000` | MinIO API |
| `9001` | MinIO console |
| `15672` | RabbitMQ management UI |
| `8081` | frontend development server |

## Health And General Routes

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/health` | basic API health check |
| `GET` | `/api/openapi.json` | generated OpenAPI schema when enabled |

## Video Routes

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/api/upload` | upload a lecture file |
| `POST` | `/api/link` | create a lecture from a generic source link |
| `POST` | `/api/youtube` | create a lecture from a YouTube source |
| `GET` | `/api/` | list lectures |
| `GET` | `/api/{video_id}` | fetch lecture metadata |
| `DELETE` | `/api/{video_id}` | delete a lecture |
| `GET` | `/api/{video_id}/status` | fetch processing status |
| `GET` | `/api/{video_id}/transcript` | fetch transcript data |
| `GET` | `/api/{video_id}/segments` | fetch topic segments |
| `POST` | `/api/{video_id}/query` | run lecture search or grounded Q&A |
| `GET` | `/api/{video_id}/slides` | fetch extracted slides |
| `GET` | `/api/{video_id}/slides/download` | download slide export |
| `GET` | `/api/{video_id}/stream` | stream lecture media |
| `GET` | `/api/{video_id}/thumbnail` | fetch lecture thumbnail |
| `GET` | `/api/{video_id}/chat` | fetch saved chat messages |
| `GET` | `/api/{video_id}/notes` | fetch generated notes |
| `POST` | `/api/{video_id}/notes/export` | export notes |

## Job Routes

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/api/jobs/{video_id}` | trigger processing |
| `GET` | `/api/jobs/{video_id}` | poll job state |
| `POST` | `/api/jobs/{video_id}/cancel` | cancel processing |

## Profile Routes

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/api/profile/me` | profile summary |
| `GET` | `/api/profile/settings` | user settings |

## Notes

- This file is intentionally a reference, not a full API specification.
- The frontend relies mainly on lecture, job, profile, notes, search, and slide routes.
- For implementation details, see:
  - `backend/app/api/videos.py`
  - `backend/app/api/jobs.py`
  - `backend/app/api/profile.py`
