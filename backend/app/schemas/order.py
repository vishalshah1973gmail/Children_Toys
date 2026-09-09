"""Order, checkout and payment schemas."""

from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.order import OrderStatus
from app.models.payment import PaymentStatus


class ShippingAddress(BaseModel):
    """Where the toys are going."""

    full_name: str = Field(..., min_length=2, max_length=120)
    line1: str = Field(..., min_length=2, max_length=200)
    line2: str | None = Field(default=None, max_length=200)
    city: str = Field(..., min_length=1, max_length=120)
    state: str = Field(..., min_length=1, max_length=120)
    postal_code: str = Field(..., min_length=3, max_length=20)
    country: str = Field(default="US", min_length=2, max_length=2)


class CheckoutRequest(BaseModel):
    """Create an order and a Stripe Checkout Session from the server-side cart."""

    contact_email: EmailStr
    shipping_address: ShippingAddress


class CheckoutSessionResponse(BaseModel):
    """Where to send the browser next."""

    order_number: str
    checkout_url: str
    session_id: str | None = None
    dev_mode: bool = False


class OrderItemRead(BaseModel):
    """A frozen order line."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    product_slug: str
    image_url: str | None = None
    unit_price_cents: int
    quantity: int
    line_total_cents: int


class PaymentRead(BaseModel):
    """A payment attempt."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    status: PaymentStatus
    amount_cents: int
    currency: str
    stripe_payment_intent_id: str | None = None
    created_at: datetime


class OrderRead(BaseModel):
    """An order as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    user_id: int | None
    status: OrderStatus
    subtotal_cents: int
    shipping_cents: int
    tax_cents: int
    total_cents: int
    currency: str
    contact_email: str
    shipping_name: str
    shipping_line1: str
    shipping_line2: str | None = None
    shipping_city: str
    shipping_state: str
    shipping_postal_code: str
    shipping_country: str
    billing_name: str | None = None
    billing_line1: str | None = None
    billing_line2: str | None = None
    billing_city: str | None = None
    billing_state: str | None = None
    billing_postal_code: str | None = None
    billing_country: str | None = None
    placed_at: datetime | None = None
    paid_at: datetime | None = None
    shipped_at: datetime | None = None
    delivered_at: datetime | None = None
    created_at: datetime
    items: List[OrderItemRead] = Field(default_factory=list)
    payments: List[PaymentRead] = Field(default_factory=list)


class OrderStatusUpdate(BaseModel):
    """Admin action advancing an order through its lifecycle."""

    status: OrderStatus
