from fastapi.testclient import TestClient

from app import __version__
from app.main import app

client = TestClient(app)


def test_root_returns_service_name():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "docqa-lite"


def test_health_returns_ok_and_version():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}
