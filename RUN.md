# Running The Backend

This project starts a FastAPI server from [app/main.py](C:/Users/deepakd2/Documents/assessment-backend/app/main.py) using the ASGI app object `app`.

## Start with `uv`, installed `uv` package is required.

From the project root `C:\Users\deepakd2\Documents\assessment-backend`:

```powershell
uv .venv
Copy-Item .env.example .env
uv run pip install -r requirements.txt
uv run uvicorn app.main:app --reload
```

The server will start on:

- `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

## What actually runs

This command starts the server:

```powershell
uv run uvicorn app.main:app --reload
```

Meaning:

- `app.main` points to [app/main.py](C:/Users/deepakd2/Documents/assessment-backend/app/main.py)
- `:app` points to the FastAPI application object defined in that file
- `--reload` enables auto-restart during development

## Local auth

The backend uses dev-mode auth by default. Pass `X-User-Email` in requests:

- Learner: `learner1@example.com`
- Reviewer: `reviewer1@example.com`
- Admin: `admin1@example.com`

If you do not send the header, the default user from `.env` is used.

## Common issues

If you already created `.venv`, you do not need to create it again. Just run:

```powershell
Copy-Item .env.example .env
uv run uvicorn app.main:app --reload
```

If dependencies are missing, run:

```powershell
uv run pip install -r requirements.txt
uv run pip install -e .[dev]
```

If port `8000` is busy, start on another port:

```powershell
uv run uvicorn app.main:app --reload --port 8001
```
