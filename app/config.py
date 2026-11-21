"""Limits and paths for the document library (see data-model.md § Constants)."""

from pathlib import Path

MAX_UPLOAD_BYTES = 1_048_576
MAX_DOCUMENTS = 100
ALLOWED_EXTENSIONS = frozenset({".md", ".markdown", ".txt"})
DEFAULT_K = 5
MIN_K = 1
MAX_K = 20
MAX_QUERY_CHARS = 500
SNIPPET_CHARS = 200
MAX_FILENAME_CHARS = 255
SAMPLE_DOCS_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_docs"
