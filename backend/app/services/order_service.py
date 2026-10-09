"""Order creation and payment confirmation.

Two rules live here and nowhere else:
  * checkout is rejected when any line exceeds available stock;
  * stock is decremented only when a payment is confirmed.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.errors import api_error
from app.core.utils import generate_order_number
from app.models.order import Order, OrderItem, OrderStatus
from app.models.payment import Payment, PaymentStatus
from app.models.user import User
from app.schemas.order import CheckoutRequest
from app.services.cart_service import load_cart_items
from app.services.pricing import totals_for


def create_pending_order(db: Session, user: User, payload: CheckoutRequest) -> Order:
    """Build a pending order from the server-side cart.

    Raises 400 when the cart is empty and 409 when stock is insufficient.
    """
    cart_items = load_cart_items(db, user)
    if not cart_items:
        raise api_error(
            status.HTTP_400_BAD_REQUEST, "empty_cart", "Your cart is empty"
        )

    for item in cart_items:
        product = item.product
        if not product.is_active:
            raise api_error(
                status.HTTP_409_CONFLICT,
                "product_unavailable",
                f"'{product.name}' is no longer available",
            )
        if item.quantity > product.stock_quantity:
            raise api_error(
                status.HTTP_409_CONFLICT,
                "insufficient_stock",
                (
                    f"Only {product.stock_quantity} of '{product.name}' left in stock "
                    f"(you asked for {item.quantity})"
                ),
                field="quantity",
            )

    subtotal = sum(item.product.price_cents * item.quantity for item in cart_items)
    totals = totals_for(subtotal)
    address = payload.shipping_address
    now = datetime.now(timezone.utc)

    order = Order(
        order_number=generate_order_number(now),
        user_id=user.id,
        status=OrderStatus.PENDING,
        currency=settings.stripe_currency,
        contact_email=str(payload.contact_email),
        shipping_name=address.full_name,
        shipping_line1=address.line1,
        shipping_line2=address.line2,
        shipping_city=address.city,
        shipping_state=address.state,
        shipping_postal_code=address.postal_code,
        shipping_country=address.country.upper(),
        placed_at=now,
        **totals,
    )

    for item in cart_items:
        product = item.product
        order.items.append(
            OrderItem(
                product_id=product.id,
                product_name=product.name,
                product_slug=product.slug,
                image_url=product.primary_image_url,
                unit_price_cents=product.price_cents,
                quantity=item.quantity,
                line_total_cents=product.price_cents * item.quantity,
            )
        )

    db.add(order)
    db.flush()
    return order


def get_order_by_number(db: Session, order_number: str) -> Order | None:
    """Fetch an order with its items and payments."""
    statement = (
        select(Order)
        .where(Order.order_number == order_number)
        .options(selectinload(Order.items), selectinload(Order.payments))
    )
    return db.execute(statement).scalar_one_or_none()


def get_order_by_session(db: Session, session_id: str) -> Order | None:
    """Fetch an order by its Stripe Checkout Session id."""
    statement = (
        select(Order)
        .where(Order.stripe_session_id == session_id)
        .options(selectinload(Order.items), selectinload(Order.payments))
    )
    return db.execute(statement).scalar_one_or_none()


def mark_order_paid(
    db: Session,
    order: Order,
    *,
    payment_intent_id: str | None = None,
    session_id: str | None = None,
    event_id: str | None = None,
    provider: str = "stripe",
) -> Order:
    """Confirm payment: decrement stock, record the payment, empty the cart.

    Idempotent — a repeated webhook for an already-paid order is a no-op.
    """
    if order.status != OrderStatus.PENDING:
        return order

    for item in order.items:
        product = item.product
        if product.stock_quantity < item.quantity:
            # Oversold between checkout and confirmation: floor at zero rather
            # than violating the non-negative stock constraint, and flag it.
            product.stock_quantity = 0
        else:
            product.stock_quantity -= item.quantity

    now = datetime.now(timezone.utc)
    order.status = OrderStatus.PAID
    order.paid_at = now
    if session_id:
        order.stripe_session_id = session_id

    db.add(
        Payment(
            order_id=order.id,
            provider=provider,
            stripe_session_id=session_id or order.stripe_session_id,
            stripe_payment_intent_id=payment_intent_id,
            stripe_event_id=event_id,
            amount_cents=order.total_cents,
            currency=order.currency,
            status=PaymentStatus.SUCCEEDED,
        )
    )

    # The purchased items leave the cart.
    for cart_item in load_cart_items(db, order.user):
        db.delete(cart_item)

    db.flush()
    return order


def record_failed_payment(
    db: Session,
    order: Order,
    reason: str,
    *,
    event_id: str | None = None,
) -> None:
    """Attach a failed payment attempt to an order without changing stock."""
    db.add(
        Payment(
            order_id=order.id,
            provider="stripe",
            stripe_session_id=order.stripe_session_id,
            stripe_event_id=event_id,
            amount_cents=order.total_cents,
            currency=order.currency,
            status=PaymentStatus.FAILED,
            failure_reason=reason,
        )
    )
    db.flush()


ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}


def advance_status(db: Session, order: Order, new_status: OrderStatus) -> Order:
    """Move an order along its lifecycle, rejecting illegal jumps."""
    if new_status == order.status:
        return order
    if new_status not in ALLOWED_TRANSITIONS[order.status]:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "invalid_status_transition",
            f"Cannot move an order from '{order.status.value}' to '{new_status.value}'",
            field="status",
        )

    now = datetime.now(timezone.utc)
    if new_status == OrderStatus.PAID:
        return mark_order_paid(db, order, provider="manual")
    if new_status == OrderStatus.SHIPPED:
        order.shipped_at = now
    elif new_status == OrderStatus.DELIVERED:
        order.delivered_at = now

    order.status = new_status
    db.flush()
    return order
