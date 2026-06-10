from typing import TypeVar, Generic
from pydantic import BaseModel

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success envelope for all API responses."""
    success: bool = True
    data: T


class PaginatedData(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standard error envelope for all API responses."""
    success: bool = False
    error: ErrorDetail
