"""Product schemas."""

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProductImageRead(BaseModel):
    """Product image as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    alt_text: str | None = None
    sort_order: int = 0
    is_primary: bool = False


class ProductImageCreate(BaseModel):
    """Attach an already-uploaded image to a product."""

    url: str = Field(..., min_length=1, max_length=500)
    alt_text: str | None = Field(default=None, max_length=255)
    sort_order: int = Field(default=0, ge=0)
    is_primary: bool = False


class ProductBase(BaseModel):
    """Editable product fields."""

    name: str = Field(..., min_length=2, max_length=200)
    description: str = Field(default="", max_length=5000)
    price_cents: int = Field(..., ge=0, le=10_000_000, description="Price in integer cents")
    stock_quantity: int = Field(default=0, ge=0, le=1_000_000)
    category_id: int = Field(..., gt=0)
    min_age_months: int = Field(default=0, ge=0, le=240)
    max_age_months: int = Field(default=192, ge=0, le=240)
    brand: str = Field(..., min_length=1, max_length=120)
    safety_notes: str | None = Field(default=None, max_length=2000)
    is_featured: bool = False
    is_active: bool = True

    @model_validator(mode="after")
    def _check_age_range(self) -> "ProductBase":
        if self.min_age_months > self.max_age_months:
            raise ValueError("min_age_months must be less than or equal to max_age_months")
        return self


class ProductCreate(ProductBase):
    """Create payload; slug is derived from the name when omitted."""

    slug: str | None = Field(default=None, max_length=220, pattern=r"^[a-z0-9-]+$")
    images: List[ProductImageCreate] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    """Partial update payload."""

    name: str | None = Field(default=None, min_length=2, max_length=200)
    slug: str | None = Field(default=None, max_length=220, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(default=None, max_length=5000)
    price_cents: int | None = Field(default=None, ge=0, le=10_000_000)
    stock_quantity: int | None = Field(default=None, ge=0, le=1_000_000)
    category_id: int | None = Field(default=None, gt=0)
    min_age_months: int | None = Field(default=None, ge=0, le=240)
    max_age_months: int | None = Field(default=None, ge=0, le=240)
    brand: str | None = Field(default=None, min_length=1, max_length=120)
    safety_notes: str | None = Field(default=None, max_length=2000)
    is_featured: bool | None = None
    is_active: bool | None = None
    images: List[ProductImageCreate] | None = None


class StockAdjustment(BaseModel):
    """Absolute or relative stock change."""

    set_to: int | None = Field(default=None, ge=0, le=1_000_000)
    delta: int | None = Field(default=None, ge=-1_000_000, le=1_000_000)

    @model_validator(mode="after")
    def _exactly_one(self) -> "StockAdjustment":
        if (self.set_to is None) == (self.delta is None):
            raise ValueError("Provide exactly one of set_to or delta")
        return self


class CategorySummary(BaseModel):
    """Minimal category shape embedded in a product."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


class ProductRead(ProductBase):
    """Product as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    category: CategorySummary
    images: List[ProductImageRead] = Field(default_factory=list)
    primary_image_url: str | None = None
    created_at: datetime
    updated_at: datetime


class UploadedImage(BaseModel):
    """Response after an admin uploads an image file."""

    url: str
    filename: str
    size_bytes: int
