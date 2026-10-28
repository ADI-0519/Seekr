# Deployment

## Overview

Seekr is designed so the frontend and backend can be deployed independently.

## Frontend

- Hosted on Vercel

The frontend expects a reachable backend API and valid Firebase configuration.

## Backend

The backend relies on:

- an API service
- worker services
- PostgreSQL
- Redis
- RabbitMQ
- MinIO
- Qdrant

For local development this is orchestrated with Docker Compose. In hosted environments, the same service boundaries still apply even if the exact infrastructure differs.

## Release Notes

For release preparation, keep the public-facing README focused on:

- what the project does
- how to run it locally
- where the live demo is
- where deeper documentation lives

Avoid publishing private credentials, internal-only hostnames, or environment-specific secrets.
