from fastapi.testclient import TestClient

from app.main import app


def test_healthcheck() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_get_me() -> None:
    with TestClient(app) as client:
        response = client.get("/me", headers={"X-User-Email": "learner1@example.com"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["user"]["email"] == "learner1@example.com"
        assert len(payload["progress"]) == 7
