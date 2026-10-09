"""Admin approve/reject of registrations."""

from unittest.mock import patch

import pytest

from app.models.user import ApprovalStatus, User, UserRole
from app.core.security import hash_password
from tests.conftest import auth_headers


@pytest.fixture
def pending_user(db):
    user = User(
        username="waiting",
        email="waiting@example.com",
        full_name="Wanda Waiting",
        hashed_password=hash_password("Toybox2026"),
        role=UserRole.CUSTOMER,
        approval_status=ApprovalStatus.PENDING,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_headers(client, admin_user):
    return auth_headers(client, "rootadmin", "Admin123!")


def test_list_defaults_to_pending_only(client, admin_headers, pending_user, customer_user):
    body = client.get("/api/admin/registrations", headers=admin_headers).json()
    assert [item["username"] for item in body["items"]] == ["waiting"]
    assert body["total"] == 1


def test_stats_counts_pending(client, admin_headers, pending_user):
    assert client.get("/api/admin/stats", headers=admin_headers).json()["pending_approvals"] == 1


def test_customer_cannot_use_registration_routes(client, customer_user, pending_user):
    headers = auth_headers(client, "shopper", "Customer123!")
    assert client.get("/api/admin/registrations", headers=headers).status_code == 403
    assert client.post(f"/api/admin/registrations/{pending_user.id}/approve", headers=headers).status_code == 403


def test_approve_unlocks_login_and_emails(client, admin_headers, pending_user, db):
    with patch("app.routers.admin.registration_service.notify_approved", return_value=True) as notify:
        response = client.post(
            f"/api/admin/registrations/{pending_user.id}/approve", headers=admin_headers
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["email_sent"] is True
    assert body["user"]["approval_status"] == "approved"
    assert body["user"]["reviewed_at"] is not None
    notify.assert_called_once()
    assert auth_headers(client, "waiting", "Toybox2026")


def test_approve_succeeds_when_email_fails(client, admin_headers, pending_user):
    with patch("app.routers.admin.registration_service.notify_approved", return_value=False):
        response = client.post(
            f"/api/admin/registrations/{pending_user.id}/approve", headers=admin_headers
        )
    assert response.status_code == 200
    assert response.json()["email_sent"] is False
    assert response.json()["user"]["approval_status"] == "approved"


def test_reject_stores_reason_blocks_login_and_emails(client, admin_headers, pending_user):
    with patch("app.routers.admin.registration_service.notify_rejected", return_value=True) as notify:
        response = client.post(
            f"/api/admin/registrations/{pending_user.id}/reject",
            json={"reason": "  Looks like a bot  "},
            headers=admin_headers,
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user"]["approval_status"] == "rejected"
    assert body["user"]["rejection_reason"] == "Looks like a bot"
    notify.assert_called_once()
    login = client.post("/api/auth/login", json={"username": "waiting", "password": "Toybox2026"})
    assert login.json()["error"]["code"] == "registration_rejected"


@pytest.mark.parametrize("reason", ["", "    ", "abcd", "x" * 501])
def test_reject_requires_a_real_reason(client, admin_headers, pending_user, db, reason):
    response = client.post(
        f"/api/admin/registrations/{pending_user.id}/reject",
        json={"reason": reason},
        headers=admin_headers,
    )
    assert response.status_code == 422
    db.expire_all()
    assert db.get(User, pending_user.id).approval_status == ApprovalStatus.PENDING


def test_second_decision_is_409_and_sends_no_email(client, admin_headers, pending_user):
    url = f"/api/admin/registrations/{pending_user.id}"
    client.post(f"{url}/approve", headers=admin_headers)
    with patch("app.routers.admin.registration_service.notify_rejected") as notify:
        response = client.post(f"{url}/reject", json={"reason": "too late now"}, headers=admin_headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "already_reviewed"
    notify.assert_not_called()
    again = client.post(f"{url}/approve", headers=admin_headers)
    assert again.status_code == 409


def test_unknown_user_is_404(client, admin_headers):
    assert client.post("/api/admin/registrations/9999/approve", headers=admin_headers).status_code == 404
