"""Domain and API models (see data-model.md)."""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.config import MAX_FILENAME_CHARS, MAX_UPLOAD_BYTES


class Document(BaseModel):
    """A stored document; immutable once created."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    filename: str = Field(min_length=1, max_length=MAX_FILENAME_CHARS)
    size_bytes: int = Field(ge=1, le=MAX_UPLOAD_BYTES)
    content: str = Field(min_length=1)
    source: Literal["sample", "upload"]


@dataclass(frozen=True)
class SearchResult:
    """A ranked match: 0 < score <= 1 (4 decimals), snippet <= SNIPPET_CHARS."""

    id: str
    title: str
    score: float
    snippet: str


class SearchHit(BaseModel):
    id: str
    title: str
    score: float
    snippet: str


class SearchResponse(BaseModel):
    query: str
    k: int
    results: list[SearchHit]


class DocumentSummary(BaseModel):
    """Public metadata for a document (data-model.md Document.id/title/filename/size_bytes)."""

    id: str
    title: str
    filename: str
    size_bytes: int


class DocumentDetail(DocumentSummary):
    """Summary plus full text (data-model.md Document.content)."""

    content: str


class DocumentList(BaseModel):
    documents: list[DocumentSummary]
    count: int
