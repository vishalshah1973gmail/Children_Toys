"""Guest order creation: pricing, stock, card gate, no Stripe involvement."""

from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.order import OrderStatus
from app.models.payment import PaymentStatus
from app.models.product import Product
from app.schemas.checkout_guest import (
    CardDetails,
    GuestAddress,
    GuestCheckoutItem,
    GuestCheckoutRequest,
)
from app.services import order_service

GOOD_CARD = CardDetails(
    brand="visa", number="4242424242424242", name_on_card="Sam Shopper",
    exp_month=12, exp_year=2030, cvv="123", postal_code="08872",
)
BILLING = GuestAddress(
    name="Sam Shopper", line1="42 Ernston Rd", city="Sayreville",
    state="NJ", postal_code="08872", country="US",
)


def _request(product_id: int, **overrides) -> GuestCheckoutRequest:
    base = dict(
        contact_email="guest@example.com",
        billing_address=BILLING,
        card=GOOD_CARD,
        same_as_billing=True,
        shipping_address=None,
        items=[GuestCheckoutItem(product_id=product_id, quantity=1)],
    )
    base.update(overrides)
    return GuestCheckoutRequest(**base)


def test_create_guest_order_marks_paid_and_decrements_stock(
    db: Session, product_factory
) -> None:
    product = product_factory(slug="guest-toy", price_cents=1599, stock=5)
    order = order_service.create_guest_order(db, _request(product.id), today=date(2026, 9, 8))
    db.commit()

    assert order.user_id is None
    assert order.status == OrderStatus.PAID
    assert order.contact_email == "guest@example.com"
    assert order.billing_name == "Sam Shopper"
    assert order.shipping_name == "Sam Shopper"  # same_as_billing copied it across
    assert order.subtotal_cents == 1599
    assert len(order.payments) == 1
    payment = order.payments[0]
    assert payment.status == PaymentStatus.SUCCEEDED
    assert payment.card_brand == "visa"
    assert payment.card_last4 == "4242"
    assert payment.provider == "guest_form"

    db.expire_all()
    assert db.get(Product, product.id).stock_quantity == 4


def test_create_guest_order_uses_explicit_shipping_when_not_same_as_billing(
    db: Session, product_factory
) -> None:
    product = product_factory(slug="guest-toy-2", price_cents=1000, stock=5)
    shipping = GuestAddress(
        name="Gift Recipient", line1="1 Other St", city="Elsewhere",
        state="NY", postal_code="10001", country="US",
    )
    order = order_service.create_guest_order(
        db, _request(product.id, same_as_billing=False, shipping_address=shipping),
        today=date(2026, 9, 8),
    )
    db.commit()
    assert order.shipping_name == "Gift Recipient"
    assert order.shipping_city == "Elsewhere"


def test_create_guest_order_rejects_empty_cart(db: Session) -> None:
    request = GuestCheckoutRequest.model_construct(
        contact_email="guest@example.com", billing_address=BILLING, card=GOOD_CARD,
        same_as_billing=True, shipping_address=None, items=[],
    )
    with pytest.raises(HTTPException) as excinfo:
        order_service.create_guest_order(db, request, today=date(2026, 9, 8))
    assert excinfo.value.detail["code"] == "empty_cart"


def test_create_guest_order_rejects_insufficient_stock(
    db: Session, product_factory
) -> None:
    product = product_factory(slug="guest-toy-3", price_cents=1000, stock=1)
    with pytest.raises(HTTPException) as excinfo:
        order_service.create_guest_order(
            db, _request(product.id, items=[GuestCheckoutItem(product_id=product.id, quantity=2)]),
            today=date(2026, 9, 8),
        )
    assert excinfo.value.detail["code"] == "insufficient_stock"


def test_create_guest_order_rejects_missing_shipping_address(
    db: Session, product_factory
) -> None:
    product = product_factory(slug="guest-toy-5", price_cents=1000, stock=5)
    with pytest.raises(HTTPException) as excinfo:
        order_service.create_guest_order(
            db,
            _request(product.id, same_as_billing=False, shipping_address=None),
            today=date(2026, 9, 8),
        )
    assert excinfo.value.detail["code"] == "missing_shipping_address"


def test_create_guest_order_aggregates_duplicate_lines_before_stock_check(
    db: Session, product_factory
) -> None:
    product = product_factory(slug="guest-toy-6", price_cents=1000, stock=1)
    with pytest.raises(HTTPException) as excinfo:
        order_service.create_guest_order(
            db,
            _request(
                product.id,
                items=[
                    GuestCheckoutItem(product_id=product.id, quantity=1),
                    GuestCheckoutItem(product_id=product.id, quantity=1),
                ],
            ),
            today=date(2026, 9, 8),
        )
    assert excinfo.value.detail["code"] == "insufficient_stock"

    db.expire_all()
    assert db.get(Product, product.id).stock_quantity == 1


def test_create_guest_order_rejects_a_bad_card(db: Session, product_factory) -> None:
    product = product_factory(slug="guest-toy-4", price_cents=1000, stock=5)
    bad_card = GOOD_CARD.model_copy(update={"number": "4242424242424241"})
    with pytest.raises(HTTPException) as excinfo:
        order_service.create_guest_order(
            db, _request(product.id, card=bad_card), today=date(2026, 9, 8)
        )
    assert excinfo.value.detail["code"] == "invalid_card"
