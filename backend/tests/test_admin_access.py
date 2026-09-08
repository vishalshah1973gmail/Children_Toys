"""Role enforcement on admin routes."""

from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def test_admin_route_blocked_for_customer(client: TestClient, customer_user, category) -> None:
    """A signed-in customer gets 403 from an admin route."""
    headers = auth_headers(client, "shopper", "Customer123!")

    response = client.post(
        "/api/admin/products",
        json={
            "name": "Sneaky Product",
            "description": "Should never be created.",
            "price_cents": 1000,
            "stock_quantity": 5,
            "category_id": category.id,
            "brand": "Nope",
        },
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"

    listing = client.get("/api/admin/products", headers=headers)
    assert listing.status_code == 403


def test_admin_route_requires_authentication(client: TestClient) -> None:
    """No token at all is a 401, not a 403."""
    response = client.get("/api/admin/orders")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_admin_can_manage_products(client: TestClient, admin_user, category) -> None:
    """An admin can create a product and adjust its stock."""
    headers = auth_headers(client, "rootadmin", "Admin123!")

    created = client.post(
        "/api/admin/products",
        json={
            "name": "Admin Made Rocket",
            "description": "Created by the admin test.",
            "price_cents": 2599,
            "stock_quantity": 7,
            "category_id": category.id,
            "min_age_months": 36,
            "max_age_months": 120,
            "brand": "Fixture Co",
            "is_featured": True,
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    product_id = created.json()["id"]
    assert created.json()["slug"] == "admin-made-rocket"

    stocked = client.patch(
        f"/api/admin/products/{product_id}/stock", json={"delta": -3}, headers=headers
    )
    assert stocked.status_code == 200
    assert stocked.json()["stock_quantity"] == 4
