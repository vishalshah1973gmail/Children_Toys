"""Payment records produced by Stripe (or the local dev payment path)."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.order import Order


class PaymentStatus(str, enum.Enum):
    """Outcome of a payment attempt."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class Payment(Base, TimestampMixin):
    """One payment attempt against an order."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="stripe")
    stripe_session_id: Mapped[str | None] = mapped_column(String(255), index=True)
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(255), index=True)
    stripe_event_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="usd")
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e]),
        default=PaymentStatus.PENDING,
        nullable=False,
        index=True,
    )
    failure_reason: Mapped[str | None] = mapped_column(Text)

    order: Mapped["Order"] = relationship(back_populates="payments")
