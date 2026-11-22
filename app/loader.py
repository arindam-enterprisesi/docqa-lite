"""Load the bundled sample documents at start-up (research.md R7)."""

import logging
import uuid
from pathlib import Path

from app.models import Document
from app.text import derive_title

logger = logging.getLogger("docqa")


def load_sample_documents(directory: Path) -> list[Document]:
    """Load every *.md file in directory, sorted by filename; skip unreadable files."""
    if not directory.is_dir():
        logger.warning("sample directory not found; no samples loaded")
        return []

    documents: list[Document] = []
    for path in sorted(directory.glob("*.md"), key=lambda p: p.name):
        try:
            raw = path.read_bytes()
            content = raw.decode("utf-8")
            document = Document(
                id=uuid.uuid4().hex,
                title=derive_title(content, path.name),
                filename=path.name,
                size_bytes=len(raw),
                content=content,
                source="sample",
            )
        except (OSError, UnicodeDecodeError, ValueError):
            logger.warning("skipped unreadable sample file=%s", path.name)
            continue
        documents.append(document)
    return documents
