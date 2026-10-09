"""Registration, login and password handling."""

from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def test_register_creates_pending_customer_without_tokens(client: TestClient, db) -> None:
    """A new account is created pending: no tokens, no sign-in."""
    response = client.post(
        "/api/auth/register",
        json={
            "username": "newparent",
            "email": "newparent@example.com",
            "full_name": "New Parent",
            "password": "Toybox2026",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "pending"
    assert "access_token" not in body and "refresh_token" not in body

    from sqlalchemy import select

    from app.models.user import ApprovalStatus, User, UserRole

    user = db.execute(select(User).where(User.username == "newparent")).scalar_one()
    assert user.role == UserRole.CUSTOMER
    assert user.approval_status == ApprovalStatus.PENDING


def test_register_rejects_duplicate_username(client: TestClient, customer_user) -> None:
    """The same username cannot be registered twice."""
    response = client.post(
        "/api/auth/register",
        json={
            "username": "shopper",
            "email": "someone.else@example.com",
            "password": "Toybox2026",
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "already_registered"


def test_login_with_wrong_password_is_rejected(client: TestClient, customer_user) -> None:
    """A bad password returns 401 and no tokens."""
    response = client.post(
        "/api/auth/login", json={"username": "shopper", "password": "NotThePassword1"}
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "invalid_credentials"
    assert "access_token" not in body


def test_login_then_refresh_and_logout(client: TestClient, customer_user) -> None:
    """A refresh token works once, then stops working after logout."""
    login = client.post(
        "/api/auth/login", json={"username": "shopper", "password": "Customer123!"}
    )
    refresh_token = login.json()["refresh_token"]

    refreshed = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]

    logout = client.post("/api/auth/logout", json={"refresh_token": refresh_token})
    assert logout.status_code == 200

    replay = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "token_revoked"


def test_change_password(client: TestClient, customer_user) -> None:
    """The old password stops working once it is changed."""
    headers = auth_headers(client, "shopper", "Customer123!")

    changed = client.post(
        "/api/auth/change-password",
        json={"current_password": "Customer123!", "new_password": "BrandNew2026"},
        headers=headers,
    )
    assert changed.status_code == 200

    old = client.post(
        "/api/auth/login", json={"username": "shopper", "password": "Customer123!"}
    )
    assert old.status_code == 401

    new = client.post(
        "/api/auth/login", json={"username": "shopper", "password": "BrandNew2026"}
    )
    assert new.status_code == 200
