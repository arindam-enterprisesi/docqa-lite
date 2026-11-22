from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """TestClient that runs the app lifespan, so each test gets a fresh library."""
    with TestClient(app) as c:
        yield c
