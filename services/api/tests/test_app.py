from fastapi.testclient import TestClient

from app.main import app
from app.settings import get_settings


def setup_module() -> None:
    get_settings.cache_clear()


def test_health_and_request_id() -> None:
    with TestClient(app) as client:
        response = client.get("/healthz", headers={"x-request-id": "health-test"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"] == "health-test"


def test_me_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_me_accepts_explicit_local_test_token(monkeypatch) -> None:
    monkeypatch.setenv("ACT_API_ALLOW_TEST_USER", "true")
    get_settings.cache_clear()

    with TestClient(app) as client:
        response = client.get("/v1/me", headers={"authorization": "Bearer prototype-test-token"})

    assert response.status_code == 200
    assert response.json() == {"id": "test-user", "role": "student"}
    get_settings.cache_clear()
