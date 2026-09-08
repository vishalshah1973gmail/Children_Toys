"""Request/response shapes for the unauthenticated guest checkout endpoint."""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.schemas.order import OrderRead

CardBrand = Literal["visa", "mastercard", "discover", "amex"]


class GuestAddress(BaseModel):
    """A billing or shipping address supplied by a guest."""

    name: str = Field(..., min_length=2, max_length=120)
    line1: str = Field(..., min_length=2, max_length=200)
    line2: str | None = Field(default=None, max_length=200)
    city: str = Field(..., min_length=1, max_length=120)
    state: str = Field(..., min_length=1, max_length=120)
    postal_code: str = Field(..., min_length=3, max_length=20)
    country: str = Field(default="US", min_length=2, max_length=2)


class CardDetails(BaseModel):
    """Card fields as typed by the guest. Never stored as-is — see card_validation."""

    brand: CardBrand
    number: str = Field(..., min_length=12, max_length=23)
    name_on_card: str = Field(..., min_length=2, max_length=120)
    exp_month: int = Field(..., ge=1, le=12)
    exp_year: int = Field(..., ge=2000, le=2100)
    cvv: str = Field(..., min_length=3, max_length=4)
    postal_code: str = Field(..., min_length=5, max_length=10)


class GuestCheckoutItem(BaseModel):
    """One cart line, as tracked client-side for a guest (no server cart)."""

    product_id: int
    quantity: int = Field(..., gt=0)


class GuestCheckoutRequest(BaseModel):
    """Everything needed to place and 'pay' a guest order in one request."""

    contact_email: EmailStr
    billing_address: GuestAddress
    card: CardDetails
    same_as_billing: bool
    shipping_address: GuestAddress | None = None
    items: list[GuestCheckoutItem] = Field(..., min_length=1)


class GuestCheckoutResponse(BaseModel):
    """The placed order, for the receipt screen, plus whether the email went out."""

    order: OrderRead
    email_sent: bool
