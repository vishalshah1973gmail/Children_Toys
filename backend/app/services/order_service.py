"""Order creation and payment confirmation.

Two rules live here and nowhere else:
  * checkout is rejected when any line exceeds available stock;
  * stock is decremented only when a payment is confirmed.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.errors import api_error
from app.core.utils import generate_order_number
from app.models.order import Order, OrderItem, OrderStatus
from app.models.payment import Payment, PaymentStatus
from app.models.product import Product
from app.models.user import User
from app.schemas.checkout_guest import GuestCheckoutRequest
from app.schemas.order import CheckoutRequest
from app.services import card_validation
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


def create_guest_order(
    db: Session,
    payload: GuestCheckoutRequest,
    *,
    today: date | None = None,
) -> Order:
    """Create and immediately mark-paid a guest order. No Stripe call ever.

    Raises 400 (empty cart or missing shipping address), 409 (stock), or
    422 (invalid_card).
    """
    if not payload.items:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "empty_cart",
            "Your cart is empty",
        )

    if not payload.same_as_billing and payload.shipping_address is None:
        raise api_error(
            status.HTTP_400_BAD_REQUEST,
            "missing_shipping_address",
            "Shipping address is required when not using billing address",
            field="shipping_address",
        )

    products: dict[int, Product] = {}
    quantities: dict[int, int] = {}
    for line in payload.items:
        product = db.get(Product, line.product_id)
        if product is None or not product.is_active:
            raise api_error(
                status.HTTP_409_CONFLICT,
                "product_unavailable",
                f"Product {line.product_id} is no longer available",
            )
        products[line.product_id] = product
        quantities[line.product_id] = quantities.get(line.product_id, 0) + line.quantity

    for product_id, total_quantity in quantities.items():
        product = products[product_id]
        if total_quantity > product.stock_quantity:
            raise api_error(
                status.HTTP_409_CONFLICT,
                "insufficient_stock",
                (
                    f"Only {product.stock_quantity} of '{product.name}' left in stock "
                    f"(you asked for {total_quantity})"
                ),
                field="quantity",
            )

    card = payload.card
    card_errors = card_validation.validate_card(
        brand=card.brand,
        number=card.number,
        exp_month=card.exp_month,
        exp_year=card.exp_year,
        cvv=card.cvv,
        postal_code=card.postal_code,
        today=today or datetime.now(timezone.utc).date(),
    )
    if card_errors:
        first = card_errors[0]
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "invalid_card",
            first.message,
            field=first.field,
        )

    subtotal = sum(
        products[line.product_id].price_cents * line.quantity for line in payload.items
    )
    totals = totals_for(subtotal)
    now = datetime.now(timezone.utc)
    billing = payload.billing_address
    shipping = billing if payload.same_as_billing else payload.shipping_address

    order = Order(
        order_number=generate_order_number(now),
        user_id=None,
        status=OrderStatus.PAID,
        currency=settings.stripe_currency,
        contact_email=str(payload.contact_email),
        billing_name=billing.name,
        billing_line1=billing.line1,
        billing_line2=billing.line2,
        billing_city=billing.city,
        billing_state=billing.state,
        billing_postal_code=billing.postal_code,
        billing_country=billing.country.upper(),
        shipping_name=shipping.name,
        shipping_line1=shipping.line1,
        shipping_line2=shipping.line2,
        shipping_city=shipping.city,
        shipping_state=shipping.state,
        shipping_postal_code=shipping.postal_code,
        shipping_country=shipping.country.upper(),
        placed_at=now,
        paid_at=now,
        **totals,
    )

    for line in payload.items:
        product = products[line.product_id]
        order.items.append(
            OrderItem(
                product_id=product.id,
                product_name=product.name,
                product_slug=product.slug,
                image_url=product.primary_image_url,
                unit_price_cents=product.price_cents,
                quantity=line.quantity,
                line_total_cents=product.price_cents * line.quantity,
            )
        )
        product.stock_quantity -= line.quantity

    digits = "".join(char for char in card.number if char.isdigit())
    order.payments.append(
        Payment(
            provider="guest_form",
            amount_cents=totals["total_cents"],
            currency=settings.stripe_currency,
            status=PaymentStatus.SUCCEEDED,
            card_brand=card.brand,
            card_last4=digits[-4:],
            card_exp_month=card.exp_month,
            card_exp_year=card.exp_year,
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
