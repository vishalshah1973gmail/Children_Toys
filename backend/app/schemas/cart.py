"""Cart schemas."""

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class CartItemCreate(BaseModel):
    """Add a product to the cart."""

    product_id: int = Field(..., gt=0)
    quantity: int = Field(default=1, gt=0, le=99)


class CartItemUpdate(BaseModel):
    """Change the quantity of an existing line."""

    quantity: int = Field(..., gt=0, le=99)


class CartMergeRequest(BaseModel):
    """Push a guest cart into the server cart after signing in."""

    items: List[CartItemCreate] = Field(default_factory=list, max_length=100)


class CartItemRead(BaseModel):
    """A cart line, priced from the server-side product record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    name: str
    slug: str
    image_url: str | None = None
    unit_price_cents: int
    quantity: int
    line_total_cents: int
    stock_quantity: int
    in_stock: bool


class CartRead(BaseModel):
    """The whole cart with server-computed totals."""

    items: List[CartItemRead]
    subtotal_cents: int
    shipping_cents: int
    tax_cents: int
    total_cents: int
    item_count: int
    currency: str = "usd"
