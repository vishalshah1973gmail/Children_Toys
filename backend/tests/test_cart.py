"""Cart behaviour, including server-side pricing."""

from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def test_add_to_cart(client: TestClient, customer_user, product_factory) -> None:
    """Adding a product returns the cart with server-computed totals."""
    product = product_factory(slug="blue-blocks", price_cents=2500, stock=10)
    headers = auth_headers(client, "shopper", "Customer123!")

    response = client.post(
        "/api/cart/items", json={"product_id": product.id, "quantity": 2}, headers=headers
    )

    assert response.status_code == 201, response.text
    cart = response.json()
    assert len(cart["items"]) == 1
    line = cart["items"][0]
    assert line["product_id"] == product.id
    assert line["quantity"] == 2
    assert line["unit_price_cents"] == 2500
    assert line["line_total_cents"] == 5000
    assert cart["subtotal_cents"] == 5000
    assert cart["shipping_cents"] == 0  # free above the 5000-cent threshold
    assert cart["total_cents"] == cart["subtotal_cents"] + cart["tax_cents"]
    assert cart["item_count"] == 2


def test_cart_ignores_any_price_sent_by_the_browser(
    client: TestClient, customer_user, product_factory
) -> None:
    """Extra fields in the request body cannot influence the price."""
    product = product_factory(slug="cheap-attempt", price_cents=4999, stock=5)
    headers = auth_headers(client, "shopper", "Customer123!")

    response = client.post(
        "/api/cart/items",
        json={"product_id": product.id, "quantity": 1, "price_cents": 1, "unit_price_cents": 1},
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["items"][0]["unit_price_cents"] == 4999
    assert response.json()["subtotal_cents"] == 4999


def test_add_to_cart_beyond_stock_is_rejected(
    client: TestClient, customer_user, product_factory
) -> None:
    """A quantity above available stock is refused with 409."""
    product = product_factory(slug="scarce-toy", price_cents=1500, stock=2)
    headers = auth_headers(client, "shopper", "Customer123!")

    response = client.post(
        "/api/cart/items", json={"product_id": product.id, "quantity": 3}, headers=headers
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "insufficient_stock"


def test_update_and_remove_cart_items(
    client: TestClient, customer_user, product_factory
) -> None:
    """Quantities can be changed and lines removed."""
    product = product_factory(slug="update-me", price_cents=1000, stock=10)
    headers = auth_headers(client, "shopper", "Customer123!")

    created = client.post(
        "/api/cart/items", json={"product_id": product.id, "quantity": 1}, headers=headers
    )
    item_id = created.json()["items"][0]["id"]

    updated = client.patch(
        f"/api/cart/items/{item_id}", json={"quantity": 4}, headers=headers
    )
    assert updated.status_code == 200
    assert updated.json()["subtotal_cents"] == 4000

    removed = client.delete(f"/api/cart/items/{item_id}", headers=headers)
    assert removed.status_code == 200
    assert removed.json()["items"] == []


def test_cart_requires_authentication(client: TestClient) -> None:
    """The cart is per-user and needs a token."""
    assert client.get("/api/cart").status_code == 401
