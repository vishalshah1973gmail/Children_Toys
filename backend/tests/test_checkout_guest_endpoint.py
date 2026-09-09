"""End-to-end guest checkout: no auth header anywhere in this file."""

from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.product import Product

GOOD_PAYLOAD_BASE = {
    "contact_email": "guest@example.com",
    "billing_address": {
        "name": "Sam Shopper", "line1": "42 Ernston Rd", "city": "Sayreville",
        "state": "NJ", "postal_code": "08872", "country": "US",
    },
    "card": {
        "brand": "visa", "number": "4242424242424242", "name_on_card": "Sam Shopper",
        "exp_month": 12, "exp_year": 2030, "cvv": "123", "postal_code": "08872",
    },
    "same_as_billing": True,
}


def test_guest_checkout_happy_path_needs_no_auth(client: TestClient, product_factory) -> None:
    product = product_factory(slug="guest-endpoint-toy", price_cents=1599, stock=5)
    payload = {**GOOD_PAYLOAD_BASE, "items": [{"product_id": product.id, "quantity": 1}]}

    with patch("app.routers.checkout.email_service.send_receipt") as mock_send:
        response = client.post("/api/checkout/guest", json=payload)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["order"]["status"] == "paid"
    assert body["order"]["user_id"] is None
    assert body["email_sent"] is True
    mock_send.assert_called_once()


def test_guest_checkout_email_failure_still_returns_the_order(
    client: TestClient, product_factory
) -> None:
    product = product_factory(slug="guest-endpoint-toy-2", price_cents=1000, stock=5)
    payload = {**GOOD_PAYLOAD_BASE, "items": [{"product_id": product.id, "quantity": 1}]}

    with patch("app.routers.checkout.email_service.send_receipt", side_effect=OSError("smtp down")):
        response = client.post("/api/checkout/guest", json=payload)

    assert response.status_code == 201, response.text
    assert response.json()["email_sent"] is False


def test_guest_checkout_rejects_insufficient_stock(client: TestClient, product_factory) -> None:
    product = product_factory(slug="guest-endpoint-toy-3", price_cents=1000, stock=1)
    payload = {**GOOD_PAYLOAD_BASE, "items": [{"product_id": product.id, "quantity": 2}]}
    response = client.post("/api/checkout/guest", json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "insufficient_stock"


def test_guest_checkout_rejects_invalid_card(client: TestClient, product_factory) -> None:
    product = product_factory(slug="guest-endpoint-toy-4", price_cents=1000, stock=5)
    bad_card = {**GOOD_PAYLOAD_BASE["card"], "number": "4242424242424241"}
    payload = {**GOOD_PAYLOAD_BASE, "card": bad_card, "items": [{"product_id": product.id, "quantity": 1}]}
    response = client.post("/api/checkout/guest", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_card"


def test_guest_checkout_decrements_stock_and_leaves_no_pending_state(
    client: TestClient, db: Session, product_factory
) -> None:
    product = product_factory(slug="guest-endpoint-toy-5", price_cents=1000, stock=5)
    payload = {**GOOD_PAYLOAD_BASE, "items": [{"product_id": product.id, "quantity": 2}]}
    with patch("app.routers.checkout.email_service.send_receipt"):
        response = client.post("/api/checkout/guest", json=payload)
    assert response.status_code == 201
    db.expire_all()
    assert db.get(Product, product.id).stock_quantity == 3
