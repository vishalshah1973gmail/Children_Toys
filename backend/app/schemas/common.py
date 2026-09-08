"""Shared response envelopes."""

from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Typed error body returned by every failure path."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable explanation")
    field: str | None = Field(default=None, description="Offending field, when applicable")


class ErrorResponse(BaseModel):
    """Envelope around a single error detail."""

    error: ErrorDetail


class Page(BaseModel, Generic[T]):
    """Generic pagination envelope."""

    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int


class Message(BaseModel):
    """Simple acknowledgement body."""

    message: str
