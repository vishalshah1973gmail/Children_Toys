"""Request and response bodies for the chat endpoint."""

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:  # pragma: no cover
    from app.models.product import Product

CHAT_MAX_CHARS = 500


class ChatRequest(BaseModel):
    message: str = Field(max_length=CHAT_MAX_CHARS * 4)
    session_id: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")

    @field_validator("message")
    @classmethod
    def _clean_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be empty.")
        if len(value) > CHAT_MAX_CHARS:
            raise ValueError(f"Message must be at most {CHAT_MAX_CHARS} characters.")
        return value


class ChatProduct(BaseModel):
    """A product mentioned in a reply, with live data for the widget's card."""

    slug: str
    name: str
    brand: str
    category_name: str
    price_cents: int
    in_stock: bool
    min_age_months: int
    max_age_months: int
    image_url: str | None = None

    @classmethod
    def from_product(cls, product: "Product") -> "ChatProduct":
        return cls(
            slug=product.slug,
            name=product.name,
            brand=product.brand,
            category_name=product.category.name,
            price_cents=product.price_cents,
            in_stock=product.stock_quantity > 0,
            min_age_months=product.min_age_months,
            max_age_months=product.max_age_months,
            image_url=product.primary_image_url,
        )


class ChatResponse(BaseModel):
    reply: str
    products: list[ChatProduct] = Field(default_factory=list)
