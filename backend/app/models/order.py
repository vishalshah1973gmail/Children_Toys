"""Order and order line item models."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.payment import Payment
    from app.models.product import Product
    from app.models.user import User


class OrderStatus(str, enum.Enum):
    """Lifecycle of an order."""

    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Order(Base, TimestampMixin):
    """A placed order. All money fields are integer cents."""

    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("total_cents >= 0", name="ck_orders_total_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e]),
        default=OrderStatus.PENDING,
        nullable=False,
        index=True,
    )

    subtotal_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    shipping_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tax_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="usd")

    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    shipping_name: Mapped[str] = mapped_column(String(120), nullable=False)
    shipping_line1: Mapped[str] = mapped_column(String(200), nullable=False)
    shipping_line2: Mapped[str | None] = mapped_column(String(200))
    shipping_city: Mapped[str] = mapped_column(String(120), nullable=False)
    shipping_state: Mapped[str] = mapped_column(String(120), nullable=False)
    shipping_postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    shipping_country: Mapped[str] = mapped_column(String(2), nullable=False, default="US")

    billing_name: Mapped[str | None] = mapped_column(String(120))
    billing_line1: Mapped[str | None] = mapped_column(String(200))
    billing_line2: Mapped[str | None] = mapped_column(String(200))
    billing_city: Mapped[str | None] = mapped_column(String(120))
    billing_state: Mapped[str | None] = mapped_column(String(120))
    billing_postal_code: Mapped[str | None] = mapped_column(String(20))
    billing_country: Mapped[str | None] = mapped_column(String(2))

    stripe_session_id: Mapped[str | None] = mapped_column(String(255), index=True)

    placed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User | None"] = relationship(back_populates="orders")
    items: Mapped[List["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    payments: Mapped[List["Payment"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Order {self.order_number} status={self.status.value} total={self.total_cents}>"


class OrderItem(Base):
    """A frozen snapshot of a product at the moment of ordering."""

    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    product_slug: Mapped[str] = mapped_column(String(220), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500))
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()
