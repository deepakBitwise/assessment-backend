# Running The Backend

This project starts a FastAPI server from [app/main.py](/abs/c:/Users/deepakd2/Documents/assessment-backend/app/main.py:1) using the ASGI app object `app`.

---

## Start with `uv`

From the project root `C:\Users\deepakd2\Documents\assessment-backend`:

```powershell
uv venv  # to initiate virtual environment, activate it if it doesn't get activated automatically.
Copy-Item .env.example .env  # to create .env of same structure as .env.example

# Install all dependencies
uv pip install -r requirements.txt

# Install MinIO SDK
uv add minio

# Run the backend server
uv run uvicorn app.main:app --reload

# To add another library
uv add library_name

