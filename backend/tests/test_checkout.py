"""Checkout rules: stock validation and deferred stock decrement."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.product import Product
from tests.conftest import auth_headers

ADDRESS = {
    "contact_email": "shopper@example.com",
    "shipping_address": {
        "full_name": "Sam Shopper",
        "line1": "42 Ernston Rd",
        "city": "Sayreville",
        "state": "NJ",
        "postal_code": "08872",
        "country": "US",
    },
}


def test_checkout_rejected_on_insufficient_stock(
    client: TestClient, db: Session, customer_user, product_factory
) -> None:
    """Stock that disappears between add-to-cart and checkout blocks the order."""
    product = product_factory(slug="last-one", price_cents=3000, stock=5)
    headers = auth_headers(client, "shopper", "Customer123!")

    added = client.post(
        "/api/cart/items", json={"product_id": product.id, "quantity": 4}, headers=headers
    )
    assert added.status_code == 201

    # Stock drops after the item is already in the cart.
    stored = db.get(Product, product.id)
    stored.stock_quantity = 1
    db.commit()

    response = client.post("/api/checkout/session", json=ADDRESS, headers=headers)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "insufficient_stock"
    assert client.get("/api/orders", headers=headers).json()["total"] == 0


def test_checkout_on_empty_cart_is_rejected(
    client: TestClient, customer_user
) -> None:
    """There is nothing to pay for."""
    headers = auth_headers(client, "shopper", "Customer123!")
    response = client.post("/api/checkout/session", json=ADDRESS, headers=headers)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "empty_cart"


def test_checkout_creates_pending_order_without_touching_stock(
    client: TestClient, db: Session, customer_user, product_factory
) -> None:
    """The order is pending and stock is untouched until payment confirms."""
    product = product_factory(slug="pending-toy", price_cents=2000, stock=6)
    headers = auth_headers(client, "shopper", "Customer123!")
    client.post(
        "/api/cart/items", json={"product_id": product.id, "quantity": 2}, headers=headers
    )

    response = client.post("/api/checkout/session", json=ADDRESS, headers=headers)
    assert response.status_code == 201, response.text
    order_number = response.json()["order_number"]

    order = client.get(f"/api/orders/{order_number}", headers=headers).json()
    assert order["status"] == "pending"
    assert order["subtotal_cents"] == 4000
    assert order["total_cents"] == order["subtotal_cents"] + order["shipping_cents"] + order["tax_cents"]

    db.expire_all()
    assert db.get(Product, product.id).stock_quantity == 6


def test_stock_decrements_only_when_payment_confirms(
    client: TestClient, db: Session, customer_user, product_factory
) -> None:
    """Confirming payment decrements stock and empties the cart."""
    product = product_factory(slug="confirm-toy", price_cents=2000, stock=6)
    headers = auth_headers(client, "shopper", "Customer123!")
    client.post(
        "/api/cart/items", json={"product_id": product.id, "quantity": 2}, headers=headers
    )
    order_number = client.post(
        "/api/checkout/session", json=ADDRESS, headers=headers
    ).json()["order_number"]

    confirmed = client.post(f"/api/checkout/dev-confirm/{order_number}", headers=headers)
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "paid"

    db.expire_all()
    assert db.get(Product, product.id).stock_quantity == 4
    assert client.get("/api/cart", headers=headers).json()["items"] == []
