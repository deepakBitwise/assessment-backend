# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Setup and run

```powershell
# Install dependencies
uv sync

# Copy env template and fill in values
Copy-Item .env.example .env

# Start infrastructure (PostgreSQL + MinIO)
docker compose up -d

# Run server with hot reload
uv run uvicorn app.main:app --reload
```

### Linting and type checking

```powershell
uv run ruff check .
uv run ruff format .
uv run mypy app
```

### Database migrations

```powershell
# Generate migration after model changes
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Fix multiple heads
uv run alembic heads
uv run alembic merge -m "merge heads" <head1> <head2>
uv run alembic upgrade head
```

### Tests

```powershell
uv run pytest
# Run single test file
uv run pytest tests/path/to/test_file.py
# Run with coverage
uv run coverage run -m pytest && uv run coverage report
```

## Architecture

This is a **FastAPI + SQLModel + PostgreSQL** backend for managing coding assessments. All models (ORM tables and Pydantic schemas) live together in `app/models.py`. `app/crud.py` holds only user and session helpers — assessment/submission logic lives directly in the route handlers.

### Request flow

```
HTTP request
  → app/main.py           (CORS, lifespan, router mount)
  → app/api/main.py       (aggregates all routers under /api/v1)
  → app/api/routes/*.py   (route handlers)
  → app/api/deps.py       (FastAPI dependency injection: DB session, current user)
  → app/crud.py           (DB operations for users/sessions only)
```

### Key domain concepts

**Single assessment model:** There is always exactly one active assessment, identified by the fixed string `DEFAULT_ASSESSMENT_ID = "assessment-1"`. `POST /assessments/` upserts rather than creates.

**Submission ID format:** IDs are human-readable strings: `{user_id}-submission-{count}`. Not UUIDs.

**Three-tier evaluation pipeline:** Each `Submission` has three independent status fields (`automated_check`, `llm_judge`, `human_reviewer`) each cycling through `PENDING → QUEUED → PASSED | REJECTED`. The Tier 1 external service call is currently commented out — `/submit` returns a mock response. Events are logged to `SubmissionEvents` (JSONB) at each step.

**File storage:** Files are never proxied through the backend. `POST /files/upload-url` returns a presigned MinIO PUT URL; the client uploads directly. The object name is stored on the `Assessment` record and copied to `Submission.attachment_object_name` at submit time. Path convention: `assessments/{assessment_id}/attachments/{filename}`.

**Auth:** OAuth2 Password Flow with JWT (HS256). Login produces both an access token (8 days) and a refresh token (30 days). The refresh token itself is **never stored** — only its Argon2 hash is persisted in `UserSession`. Logout soft-deletes sessions (`is_active = False`).

### Seed users (local environment only)

On startup in `ENVIRONMENT=local`, `app/core/db.py:init_db()` auto-creates these users:

| Email | Username | Password | Role |
|---|---|---|---|
| admin@example.com | (from env) | (from env) | ADMIN / superuser |
| admin.user@example.com | admin.user | SecurePass123! | ADMIN / superuser |
| reviewer@example.com | reviewer | SecurePass123! | REVIEWER |
| learner@example.com | learner | SecurePass123! | LEARNER |

### Environment variables

Required (no default): `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`.

The MinIO client is initialized at import time in `app/core/minio_config.py` — if MinIO is unreachable on startup the server will fail to start.

`TIER1_JOB_URL` / `TIER1_SERVICE_TOKEN` are for the external automated evaluation service (currently unused — the call is commented out in `submission.py`).

`PRIVATE_ROUTER` routes are only registered in `ENVIRONMENT=local` (see `app/api/main.py`).
