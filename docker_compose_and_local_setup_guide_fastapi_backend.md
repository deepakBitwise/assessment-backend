# FastAPI Backend Local Setup Guide

## Prerequisites

Before running the project locally, ensure the following are installed:

### 1. Docker Desktop
Install Docker Desktop:
https://www.docker.com/products/docker-desktop/

Verify installation:

```bash
docker --version
```

---

### 2. Python
Recommended Python version:

```text
Python 3.11 or 3.12
```

Verify installation:

```bash
python --version
```

---

### 3. Git
Verify installation:

```bash
git --version
```

---

# Project Setup

## 1. Clone Repository

```bash
git clone <YOUR_GIT_REPOSITORY_URL>
cd assessment-backend
```

---

# 2. Create Virtual Environment

## Windows

```bash
python -m venv venv
venv\Scripts\activate
```

## Mac/Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

---

# 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

# 4. Create .env File

Create a file named:

```text
.env
```

Add the following:

```env
PROJECT_NAME="Assessment Backend"

API_V1_STR=/api/v1

SECRET_KEY=supersecretkey123
ACCESS_TOKEN_EXPIRE_MINUTES=10080

POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=app

FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=admin123

MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=assessment-files
MINIO_SECURE=false
```

---

# 5. Docker Compose Setup

Create a file named:

```text
docker-compose.yml
```

Add the following:

```yaml
version: '3.9'

services:
  postgres:
    image: postgres:latest
    container_name: assessment-postgres
    restart: always
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: app
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  minio:
    image: quay.io/minio/minio
    container_name: assessment-minio
    restart: always
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

volumes:
  postgres_data:
  minio_data:
```

---

# 6. Start Docker Services

Run:

```bash
docker compose up -d
```

Verify containers are running:

```bash
docker ps
```

Expected containers:

- assessment-postgres
- assessment-minio

---

# 7. Run Database Migrations

```bash
python -m alembic upgrade head
```

---

# 8. Create Initial Superuser

```bash
python -c "from app.core.db import engine, init_db; from sqlmodel import Session; session = Session(engine); init_db(session)"
```

---

# 9. Start FastAPI Server

```bash
uvicorn app.main:app --reload
```

Expected output:

```text
Application startup complete.
```

---

# 10. Open Swagger Docs

Open:

```text
http://127.0.0.1:8000/docs
```

---

# Authentication Testing

## Login Endpoint

Use:

```text
POST /api/v1/login/access-token
```

Credentials:

```text
username: admin@example.com
password: admin123
```

Expected response:

```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

---

# Test Protected Route

## 1. Click Authorize

Paste:

```text
Bearer YOUR_ACCESS_TOKEN
```

---

## 2. Test:

```text
POST /api/v1/login/test-token
```

Expected:

```json
{
  "email": "admin@example.com"
}
```

---

# Useful Docker Commands

## Start Containers

```bash
docker compose up -d
```

---

## Stop Containers

```bash
docker compose down
```

---

## Restart Containers

```bash
docker compose restart
```

---

## View Running Containers

```bash
docker ps
```

---

# MinIO Console

Open:

```text
http://localhost:9001
```

Login:

```text
username: minioadmin
password: minioadmin
```

---

# Common Issues

## Port Already In Use

Stop old containers:

```bash
docker compose down
```

Then restart:

```bash
docker compose up -d
```

---

## PostgreSQL Connection Error

Ensure Docker containers are running:

```bash
docker ps
```

---

## Missing Dependencies

Run:

```bash
pip install -r requirements.txt
```

---

# Recommended Git Ignore

Ensure `.gitignore` contains:

```gitignore
venv/
.env
__pycache__/
*.pyc
.idea/
.vscode/
```

---

# Final Stack

This project uses:

- FastAPI
- PostgreSQL
- Docker
- SQLModel
- Alembic
- JWT Authentication
- MinIO
- Swagger/OpenAPI

