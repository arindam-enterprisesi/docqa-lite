import logging
import threading
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile

from app import __version__
from app.config import (
    DEFAULT_K,
    MAX_K,
    MAX_QUERY_CHARS,
    MAX_UPLOAD_BYTES,
    MIN_K,
    SAMPLE_DOCS_DIR,
)
from app.loader import load_sample_documents
from app.logging_filters import install_query_redaction
from app.models import (
    Document,
    DocumentDetail,
    DocumentList,
    DocumentSummary,
    SearchHit,
    SearchResponse,
)
from app.repository import InMemoryDocumentRepository, LibraryFullError
from app.search import SearchIndex
from app.text import decode_utf8, derive_title, has_allowed_extension, safe_filename

logger = logging.getLogger("docqa")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create a fresh in-memory library and index, and load the sample documents."""
    install_query_redaction()
    repository = InMemoryDocumentRepository()
    for document in load_sample_documents(SAMPLE_DOCS_DIR):
        repository.add(document)
    index = SearchIndex()
    index.rebuild(repository.list())
    app.state.repository = repository
    app.state.index = index
    app.state.write_lock = threading.Lock()
    logger.info("library ready documents=%d", repository.count())
    yield


app = FastAPI(title="docqa-lite", version=__version__, lifespan=lifespan)


def get_repository(request: Request) -> InMemoryDocumentRepository:
    """Dependency: the repository for the running app (override to swap storage)."""
    return request.app.state.repository


def get_index(request: Request) -> SearchIndex:
    """Dependency: the search index for the running app."""
    return request.app.state.index


RepositoryDep = Annotated[InMemoryDocumentRepository, Depends(get_repository)]
IndexDep = Annotated[SearchIndex, Depends(get_index)]


@app.get("/")
def root() -> dict[str, str]:
    """Basic service info."""
    return {"name": "docqa-lite", "version": __version__}


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check with the service version."""
    return {"status": "ok", "version": __version__}


@app.get("/search", response_model=SearchResponse)
def search(
    q: Annotated[str, Query(description="Search text, 1-500 characters after trimming")],
    index: IndexDep,
    k: Annotated[int, Query(ge=MIN_K, le=MAX_K, description="Maximum number of results")] = (
        DEFAULT_K
    ),
) -> SearchResponse:
    """Rank documents against the query with TF-IDF cosine similarity."""
    query = q.strip()
    if not query:
        raise HTTPException(status_code=422, detail="Query must not be blank")
    if len(query) > MAX_QUERY_CHARS:
        raise HTTPException(
            status_code=422, detail=f"Query too long: maximum {MAX_QUERY_CHARS} characters"
        )
    results = index.search(query, k)
    logger.info("search completed results=%d", len(results))
    return SearchResponse(
        query=query,
        k=k,
        results=[
            SearchHit(id=r.id, title=r.title, score=r.score, snippet=r.snippet) for r in results
        ],
    )


def _summary(document: Document) -> DocumentSummary:
    return DocumentSummary(
        id=document.id,
        title=document.title,
        filename=document.filename,
        size_bytes=document.size_bytes,
    )


@app.post("/documents", status_code=201, response_model=DocumentSummary)
def upload_document(
    request: Request,
    file: Annotated[UploadFile, File()],
    repository: RepositoryDep,
    index: IndexDep,
) -> DocumentSummary:
    """Store a .md/.markdown/.txt UTF-8 file (<= 1 MB) and make it searchable."""
    filename = safe_filename(file.filename or "")
    if not filename or not has_allowed_extension(filename):
        raise HTTPException(
            status_code=415, detail="Unsupported file type: allowed .md, .markdown, .txt"
        )
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413, detail=f"File too large: maximum {MAX_UPLOAD_BYTES} bytes"
        )
    if not data:
        raise HTTPException(status_code=422, detail="File is empty")
    try:
        content = decode_utf8(data)
    except ValueError:
        raise HTTPException(status_code=422, detail="File is not valid UTF-8 text") from None

    document = Document(
        id=uuid.uuid4().hex,
        title=derive_title(content, filename),
        filename=filename,
        size_bytes=len(data),
        content=content,
        source="upload",
    )
    # One lock around add + rebuild so a concurrent upload can't publish a stale index.
    with request.app.state.write_lock:
        try:
            repository.add(document)
        except LibraryFullError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from None
        index.rebuild(repository.list())
    logger.info("document stored id=%s bytes=%d", document.id, document.size_bytes)
    return _summary(document)


@app.get("/documents", response_model=DocumentList)
def list_documents(
    repository: RepositoryDep,
) -> DocumentList:
    """List document metadata (no content) in library order."""
    documents = [_summary(d) for d in repository.list()]
    return DocumentList(documents=documents, count=len(documents))


@app.get("/documents/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: str,
    repository: RepositoryDep,
) -> DocumentDetail:
    """Return one document with its full content, or 404."""
    document = repository.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentDetail(**_summary(document).model_dump(), content=document.content)
