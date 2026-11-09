"""Common generic schemas and pagination structures."""

from typing import Generic, List, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema with standard Pydantic v2 configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


class PaginatedResponse(BaseSchema, Generic[T]):
    """Standard pagination wrapper for list responses."""

    items: List[T]
    total: int = Field(..., ge=0, description="Total count of items matching query")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Number of items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
