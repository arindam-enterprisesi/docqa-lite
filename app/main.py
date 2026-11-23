import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile

from app import __version__
from app.ingest import (
    MAX_BYTES,
    MAX_DOCUMENTS,
    UploadRejected,
    check_extension,
    decode_upload,
    extract_title,
    load_sample_dir,
    new_id,
    sanitize_filename,
)
from app.models import DocumentOut, DocumentSummary, SearchResponse
from app.repository import Document, InMemoryDocumentRepository
from app.search import SearchIndex

logger = logging.getLogger("docqa")

DEFAULT_SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_docs"


def create_app(sample_dir: Path | None = DEFAULT_SAMPLE_DIR) -> FastAPI:
    """Build a fresh app with its own in-memory library (samples loaded at start-up)."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        repository = InMemoryDocumentRepository()
        for doc in load_sample_dir(sample_dir):
            repository.add(doc)
        index = SearchIndex()
        index.rebuild(repository.list())
        app.state.repository = repository
        app.state.index = index
        app.state.lock = threading.Lock()
        logger.info("library_ready documents=%d", len(repository.list()))
        yield

    app = FastAPI(title="docqa-lite", version=__version__, lifespan=lifespan)

    @app.get("/")
    def root() -> dict[str, str]:
        """Basic service info."""
        return {"name": "docqa-lite", "version": __version__}

    @app.get("/health")
    def health() -> dict[str, str]:
        """Liveness check."""
        return {"status": "ok", "version": __version__}

    @app.post("/documents", status_code=201, response_model=DocumentSummary)
    def upload_document(request: Request, file: Annotated[UploadFile, File()]) -> DocumentSummary:
        """Upload a .md, .markdown or .txt file (UTF-8, at most 1 MB); it is searchable at once.

        Rejected with 409 once the library holds the maximum number of documents.
        """
        filename = sanitize_filename(file.filename or "")
        try:
            check_extension(filename)
            data = file.file.read(MAX_BYTES + 1)  # bounded read: never trust Content-Length
            content = decode_upload(data)
        except UploadRejected as exc:
            raise HTTPException(exc.status_code, exc.detail) from None
        doc = Document(
            id=new_id(),
            title=extract_title(content, filename),
            filename=filename,
            size=len(data),
            content=content,
            source="upload",
        )
        state = request.app.state
        with state.lock:
            if len(state.repository.list()) >= MAX_DOCUMENTS:
                raise HTTPException(
                    409, f"Library is full; the maximum is {MAX_DOCUMENTS} documents"
                )
            state.repository.add(doc)
            state.index.rebuild(state.repository.list())
        logger.info("document_added id=%s filename=%s size=%d", doc.id, doc.filename, doc.size)
        return DocumentSummary.model_validate(doc)

    @app.get("/documents", response_model=list[DocumentSummary])
    def list_documents(request: Request) -> list[DocumentSummary]:
        """All documents (metadata only), samples first, then uploads in upload order."""
        return [DocumentSummary.model_validate(d) for d in request.app.state.repository.list()]

    @app.get("/documents/{document_id}", response_model=DocumentOut)
    def get_document(request: Request, document_id: str) -> DocumentOut:
        """One document including its full content."""
        doc = request.app.state.repository.get(document_id)
        if doc is None:
            raise HTTPException(404, "Document not found")
        return DocumentOut.model_validate(doc)

    @app.get("/search", response_model=SearchResponse)
    def search(
        request: Request,
        q: str = Query(min_length=1, max_length=500, description="Text query"),
        k: int = Query(5, ge=1, le=20, description="Maximum number of results"),
    ) -> SearchResponse:
        """Rank documents by TF-IDF relevance to the query (query text is never logged)."""
        query = q.strip()
        if not query:
            raise HTTPException(422, "Query must contain non-whitespace characters")
        results = request.app.state.index.search(query, k)
        return SearchResponse(query=query, k=k, results=results)

    return app


app = create_app()
