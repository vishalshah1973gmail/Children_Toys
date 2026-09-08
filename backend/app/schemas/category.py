"""Category schemas."""

from pydantic import BaseModel, ConfigDict, Field


class CategoryBase(BaseModel):
    """Editable category fields."""

    name: str = Field(..., min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    image_url: str | None = Field(default=None, max_length=500)


class CategoryCreate(CategoryBase):
    """Create payload; slug is derived server-side when omitted."""

    slug: str | None = Field(default=None, max_length=140, pattern=r"^[a-z0-9-]+$")


class CategoryUpdate(BaseModel):
    """Partial update payload."""

    name: str | None = Field(default=None, min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=140, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(default=None, max_length=2000)
    image_url: str | None = Field(default=None, max_length=500)


class CategoryRead(CategoryBase):
    """Category as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    product_count: int = 0
