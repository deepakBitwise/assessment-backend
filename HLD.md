# High Level Design — Assessment Backend

## 1. Overview

A FastAPI-based REST backend for managing coding assessments with a **three-tier evaluation pipeline**: automated checks → LLM judging → human review. It handles user management, file storage, submission tracking, and evaluation orchestration.

---

## 2. System Architecture

```
Clients (Frontend / External Services)
        | HTTPS
        v
FastAPI Backend  (app/main.py)
  +----------+  +----------+  +------------+  +-------------+
  | Auth /   |  | Users /  |  | Assessment |  |   Human     |
  | Sessions |  |  Items   |  | /Submission|  |   Review    |
  +----------+  +----------+  +------------+  +-------------+
  +----------+  +----------+  +----------+
  |  Files   |  |  CRUD    |  |  Utils   |
  | (MinIO)  |  |  Layer   |  |  /Email  |
  +----------+  +----------+  +----------+
        |               |              |
  PostgreSQL          MinIO       Tier1 Service
  (SQLModel)      (S3-compat)    (External eval)
```

---

## 3. Module Structure

```
app/
├── main.py             # App entrypoint, CORS, lifespan, router registration
├── models.py           # SQLModel ORM models + Pydantic schemas
├── crud.py             # Database access layer (users, sessions, items)
├── utils.py            # Email rendering, token helpers, datetime utils
├── core/
│   ├── config.py       # Settings (env vars, computed properties)
│   ├── db.py           # SQLAlchemy engine + session factory
│   ├── security.py     # JWT creation/verification, password hashing
│   └── minio_config.py # MinIO client initialization
└── api/
    ├── main.py         # Aggregates all routers under /api/v1
    ├── deps.py         # FastAPI dependency injections
    └── routes/
        ├── login.py        # Auth endpoints
        ├── users.py        # User CRUD + registration
        ├── assessment.py   # Assessment management
        ├── submission.py   # Submission creation + event tracking
        ├── human_review.py # Manual review workflow
        ├── files.py        # Presigned URL generation (MinIO)
        └── utils.py        # Health check, test email
```

---

## 4. Data Models

```
User
  id (UUID), email, username, hashed_password
  role: LEARNER | REVIEWER | ADMIN
  is_active, is_superuser
  |---> UserSession (1:N)  — refresh_token_hash, device/IP, expiry
  |---> Item (1:N)         — title, description
  +---> Submission (1:N)
         id: {user_id}-submission-{n}
         automated_check / llm_judge / human_reviewer:
           PENDING | QUEUED | PASSED | REJECTED
         |---> SubmissionEvents  — JSONB event log
         +---> HumanReview       — reviewer_id, comments, verdict

Assessment
  id (fixed DEFAULT_ASSESSMENT_ID)
  problem_statement, deliverables (JSONB), attachment_object_name
```

---

## 5. Authentication & Authorization

**Mechanism:** OAuth2 Password Flow + JWT (HS256) + Refresh Tokens

- Login produces an **access token** (8 days) + **refresh token** (30 days) + `UserSession` record
- Refresh token stored as **hash only** — plain token is never persisted
- Logout marks `session.is_active = False` (single session or all devices)

### Access Control

| Dependency | Guards |
|---|---|
| `CurrentUser` | Any authenticated endpoint |
| `get_current_active_superuser` | Admin-only operations |
| Role checks (REVIEWER / ADMIN) | Human review, submission management |
| Owner check | Users can only modify their own resources |

---

## 6. Submission & Evaluation Pipeline

```
POST /submit  ->  Submission created (all tiers = PENDING)
                      |
         +------------v------------+
         |  Tier 1: Automated      |  <- External Tier1 Service
         |  automated_check        |
         +------------+------------+
                      |
         +------------v------------+
         |  Tier 2: LLM Judge      |  <- External LLM
         |  llm_judge              |
         +------------+------------+
                      |
         +------------v------------+
         |  Tier 3: Human Review   |  <- Internal reviewer via API
         |  human_reviewer         |
         +-------------------------+

Each tier:  PENDING -> QUEUED -> PASSED | REJECTED
Events logged to SubmissionEvents (JSONB) at every step.
```

---

## 7. File Storage (MinIO)

Files are **never proxied** through the backend — clients interact directly with MinIO via short-lived presigned URLs (15-minute expiry).

- **Upload:** `POST /files/upload-url` → returns presigned PUT URL
- **Download:** `GET /files/download-url/{object_name}` → returns presigned GET URL
- **Path convention:** `assessments/{assessment_id}/attachments/{filename}`

---

## 8. API Surface Summary

| Group | Prefix | Key Endpoints |
|---|---|---|
| Auth | `/api/v1/login` | access-token, refresh, logout, sessions |
| Users | `/api/v1/users` | signup, me, CRUD (admin) |
| Assessment | `/api/v1/assessments` | create / update / get |
| Submission | `/api/v1/submit`, `/api/v1/submissions` | submit, list, status update, events |
| Human Review | `/api/v1/human-reviews` | create, list, update verdict |
| Files | `/api/v1/files` | upload-url, download-url |
| Utils | `/api/v1/utils` | health-check, test-email |

---

## 9. Infrastructure & Configuration

| Component | Technology |
|---|---|
| Framework | FastAPI (Python) |
| ORM | SQLModel (SQLAlchemy + Pydantic) |
| Database | PostgreSQL 16 |
| Migrations | Alembic |
| File Storage | MinIO (S3-compatible) |
| Auth | OAuth2 + JWT, pwdlib (Argon2 + bcrypt) |
| Email | SMTP + Jinja2 templates |
| Error Tracking | Sentry (optional) |
| Containerization | Docker + Docker Compose |

**Key environment variables:**

| Variable | Purpose |
|---|---|
| `POSTGRES_*` | Database connection |
| `SECRET_KEY` | JWT signing key |
| `MINIO_*` | File storage connection |
| `TIER1_JOB_URL`, `TIER1_SERVICE_TOKEN` | External evaluation service |
| `SENTRY_DSN` | Error tracking (optional) |
| `SMTP_*` | Email config (optional) |
| `FIRST_SUPERUSER*` | Bootstrap admin credentials |

---

## 10. Key Design Decisions

- **Single assessment:** One active assessment at a time via a fixed `DEFAULT_ASSESSMENT_ID`.
- **Submission ID format:** Human-readable `{user_id}-submission-{count}` instead of UUID.
- **Refresh token security:** Only the token hash is persisted — the plain token is never stored.
- **JSONB for flexible data:** Deliverables, events, and evaluator payloads use JSONB to avoid rigid schema for evolving structures.
- **Presigned URLs:** Clients upload/download directly to MinIO — no file proxying through the backend.
- **Three independent tiers:** Each evaluation tier is tracked separately, enabling granular retries and partial progress visibility.
