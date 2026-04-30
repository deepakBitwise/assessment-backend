# Assessment Backend

Production-oriented FastAPI backend scaffold for the DIFY FDE assessment platform described in `DIFY_FDE_Assessment_Platform_Design.docx`.

## What is included

- FastAPI service with learner, reviewer, and admin routes.
- Async SQLAlchemy persistence with SQLite by default and PostgreSQL-ready models.
- Seeded seven-level learning path, assessment specs, rubric thresholds, and cohort data.
- Immutable attempts/submissions model with audit logging.
- Local upload flow that mirrors pre-signed upload semantics for frontend integration.
- Evaluation orchestration stubs for deterministic checks, judge runs, and review queueing.
- Role-aware auth abstraction with a dev header mode for local UI integration.

## Quick start

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`.

## Local auth

By default the API runs in `AUTH_MODE=dev`.

- Learner requests: `X-User-Email: learner1@example.com`
- Reviewer requests: `X-User-Email: reviewer1@example.com`
- Admin requests: `X-User-Email: admin1@example.com`

If the header is omitted, `DEV_DEFAULT_USER_EMAIL` is used.

## Upload flow

1. `POST /uploads/presign`
2. `PUT /uploads/{upload_token}`
3. `POST /attempts/{attempt_id}/submissions`

This mirrors a browser-to-object-store upload dance, but uses local disk in development. Swap `LocalStorageService` for S3 or MinIO in production.

## Production notes

- Set `DATABASE_URL` to PostgreSQL.
- Replace `AUTH_MODE=dev` with your OIDC integration.
- Replace stub evaluator and judge adapters with DIFY, sandbox, and model services.
- Move uploaded artifacts to S3 or MinIO and put this service behind a reverse proxy.
