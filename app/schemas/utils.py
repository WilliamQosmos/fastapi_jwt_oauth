from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseOffsetPagination(BaseModel, Generic[T]):
    total: int
    offset: int
    limit: int
    items: list[T]


class CommonQueryParams(BaseModel):
    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)


class ReferrerIdParam(BaseModel):
    referrer_id: str = Field(..., max_length=100)


class ReferrerIdCommonParams(CommonQueryParams, ReferrerIdParam):
    pass


class OrderBy(str, Enum):
    asc = "asc"
    desc = "desc"
