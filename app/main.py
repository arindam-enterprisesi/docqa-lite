from fastapi import FastAPI

from app import __version__

app = FastAPI(title="docqa-lite", version=__version__)


@app.get("/")
def root() -> dict[str, str]:
    """Basic service info."""
    return {"name": "docqa-lite", "version": __version__}
