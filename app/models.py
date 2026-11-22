"""Pydantic v2 response models (see contracts/openapi.yaml)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DocumentSummary(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: str
    title: str = Field(min_length=1, max_length=200)
    filename: str = Field(min_length=1, max_length=255)
    size: int = Field(ge=1, le=1_048_576)
    source: Literal["sample", "upload"]


class DocumentOut(DocumentSummary):
    content: str


class SearchHit(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    score: float = Field(gt=0, le=1)
    snippet: str = Field(max_length=200)


class SearchResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str
    k: int
    results: list[SearchHit]
