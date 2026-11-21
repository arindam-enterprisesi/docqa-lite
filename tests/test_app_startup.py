from fastapi.testclient import TestClient

from app.main import app, get_repository


def test_lifespan_loads_five_sample_documents(client):
    assert client.app.state.repository.count() == 5


def test_each_client_starts_with_a_fresh_library():
    with TestClient(app) as first:
        repo = first.app.state.repository
        assert repo.count() == 5
    with TestClient(app) as second:
        assert second.app.state.repository.count() == 5
        assert second.app.state.repository is not repo


def test_get_repository_returns_app_state_repository(client):
    class FakeRequest:
        app = client.app

    assert get_repository(FakeRequest()) is client.app.state.repository
