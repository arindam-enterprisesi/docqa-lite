from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_docs"


@pytest.fixture
def sample_dir() -> Path:
    """Absolute path to the bundled sample documents."""
    return SAMPLE_DIR


@pytest.fixture
def make_sample_dir(tmp_path: Path) -> Callable[[dict[str, bytes]], Path]:
    """Factory: write ``{filename: bytes}`` into a fresh temp directory and return it."""
    counter = 0

    def _make(files: dict[str, bytes]) -> Path:
        nonlocal counter
        counter += 1
        directory = tmp_path / f"samples-{counter}"
        directory.mkdir()
        for name, data in files.items():
            (directory / name).write_bytes(data)
        return directory

    return _make


@pytest.fixture
def make_client() -> Iterator[Callable[..., TestClient]]:
    """Factory returning a started TestClient (lifespan run) for a fresh app."""
    from app.main import create_app  # imported lazily so collection works before it exists

    clients: list[TestClient] = []

    def _make(sample_dir: Path | None = SAMPLE_DIR) -> TestClient:
        client = TestClient(create_app(sample_dir=sample_dir))
        client.__enter__()
        clients.append(client)
        return client

    yield _make
    for client in clients:
        client.__exit__(None, None, None)


@pytest.fixture
def client(make_client: Callable[..., TestClient]) -> TestClient:
    """A started TestClient over a fresh library holding the five sample documents."""
    return make_client()
