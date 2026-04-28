"""Standard API envelopes."""

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | list[Any] | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


class PaginatedMeta(BaseModel):
    """Standard list pagination envelope (blueprint)."""

    total: int
    limit: int
    offset: int


class PaginatedResponse(BaseModel):
    data: list[Any]
    total: int = Field(..., description="Total matching rows")
    limit: int
    offset: int
