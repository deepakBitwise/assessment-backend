# Running The Backend

This project starts a FastAPI server from [app/main.py](/abs/c:/Users/deepakd2/Documents/assessment-backend/app/main.py:1) using the ASGI app object `app`.

## Start with `uv`

From the project root `C:\Users\deepakd2\Documents\assessment-backend`:

```powershell
uv sync
uv run fastapi dev app/main.py
```

The server will start on:

- `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/api/v1/utils/health-check/`

## What actually runs

This command starts the server:

```powershell
uv run fastapi dev app/main.py
```

Meaning:

- `app/main.py` is the FastAPI entrypoint file
- the `app` object inside that file is loaded by the FastAPI CLI
- `dev` enables the local development server with auto-reload

## Notes

- The app now reads `.env` from the repo root if you want to override defaults locally.
- For a quick local run, no extra env setup is required.
- If port `8000` is busy, use `uv run fastapi dev app/main.py --port 8001`
