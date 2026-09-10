from pydantic import BaseModel, Field


class Page[T](BaseModel):
    """A single offset-based page of results."""

    items: list[T]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
