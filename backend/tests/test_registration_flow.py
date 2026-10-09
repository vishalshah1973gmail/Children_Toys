"""Register -> login gating -> token invalidation -> re-apply."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.models.user import ApprovalStatus, User, UserRole
from tests.conftest import auth_headers

PAYLOAD = {
    "username": "newparent",
    "email": "newparent@example.com",
    "full_name": "New Parent",
    "password": "Toybox2026",
}


def _register(client, **overrides):
    return client.post("/api/auth/register", json={**PAYLOAD, **overrides})


def _get(db, username) -> User:
    db.expire_all()
    return db.execute(select(User).where(User.username == username)).scalar_one()


def test_register_notifies_admin(client):
    with patch("app.routers.auth.registration_service.notify_admin_new_registration") as notify:
        notify.return_value = True
        assert _register(client).status_code == 201
    notify.assert_called_once()


def test_register_succeeds_when_email_fails(client):
    with patch(
        "app.routers.auth.registration_service.notify_admin_new_registration", return_value=False
    ):
        assert _register(client).status_code == 201


def test_pending_user_cannot_login(client):
    _register(client)
    response = client.post(
        "/api/auth/login", json={"username": "newparent", "password": "Toybox2026"}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "approval_pending"


def test_pending_user_wrong_password_still_generic_401(client):
    _register(client)
    response = client.post("/api/auth/login", json={"username": "newparent", "password": "Wrong123456"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_rejected_user_login_shows_reason(client, db):
    _register(client)
    user = _get(db, "newparent")
    user.approval_status = ApprovalStatus.REJECTED
    user.rejection_reason = "Email domain not allowed"
    db.commit()

    response = client.post(
        "/api/auth/login", json={"username": "newparent", "password": "Toybox2026"}
    )
    assert response.status_code == 403
    error = response.json()["error"]
    assert error["code"] == "registration_rejected"
    assert "Email domain not allowed" in error["message"]


def test_approved_user_can_login(client, db):
    _register(client)
    user = _get(db, "newparent")
    user.approval_status = ApprovalStatus.APPROVED
    db.commit()
    assert auth_headers(client, "newparent", "Toybox2026")


def test_tokens_stop_working_when_user_later_rejected(client, db):
    _register(client)
    user = _get(db, "newparent")
    user.approval_status = ApprovalStatus.APPROVED
    db.commit()
    login = client.post("/api/auth/login", json={"username": "newparent", "password": "Toybox2026"})
    tokens = login.json()

    user = _get(db, "newparent")
    user.approval_status = ApprovalStatus.REJECTED
    user.rejection_reason = "Changed our mind"
    db.commit()

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 401
    refresh = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 401


def test_duplicate_pending_registration_is_409(client):
    _register(client)
    response = _register(client, email="other@example.com")
    assert response.status_code == 409
    assert response.json()["error"]["field"] == "username"


def test_username_and_email_owned_by_different_users_is_clean_409(client, customer_user, admin_user):
    response = _register(client, username="shopper", email="rootadmin@example.com")
    assert response.status_code == 409


def test_rejected_user_can_reapply(client, db):
    _register(client)
    user = _get(db, "newparent")
    user.approval_status = ApprovalStatus.REJECTED
    user.rejection_reason = "No"
    user.reviewed_at = datetime.now(timezone.utc)
    db.commit()

    with patch("app.routers.auth.registration_service.notify_admin_new_registration") as notify:
        response = _register(client, full_name="Better Name", password="NewPass2026")
    assert response.status_code == 201
    notify.assert_called_once()

    user = _get(db, "newparent")
    assert user.approval_status == ApprovalStatus.PENDING
    assert user.rejection_reason is None
    assert user.reviewed_at is None
    assert user.full_name == "Better Name"
    from app.core.security import verify_password

    assert verify_password("NewPass2026", user.hashed_password)
