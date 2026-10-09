"""Registration emails: rendering, escaping and best-effort sending."""

from unittest.mock import patch

import pytest

from app.core.config import settings
from app.models.user import ApprovalStatus, User, UserRole
from app.services import email_service, registration_service


@pytest.fixture
def smtp_on(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "smtp.test")
    monkeypatch.setattr(settings, "smtp_user", "bot@test")
    monkeypatch.setattr(settings, "smtp_app_password", "pw")
    monkeypatch.setattr(settings, "email_from", "ToyBox <bot@test>")
    monkeypatch.setattr(settings, "admin_notify_email", "boss@test")
    monkeypatch.setattr(settings, "frontend_base_url", "http://shop.test")


def _applicant(**overrides) -> User:
    data = dict(
        username="newparent",
        email="np@example.com",
        full_name="New Parent",
        hashed_password="x",
        role=UserRole.CUSTOMER,
        approval_status=ApprovalStatus.PENDING,
    )
    data.update(overrides)
    return User(**data)


def test_send_mail_raises_when_smtp_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "")
    with pytest.raises(email_service.EmailNotConfigured):
        email_service.send_mail("a@b.c", "s", "<p>x</p>")


def test_send_mail_uses_smtp(smtp_on):
    with patch("app.services.email_service.smtplib.SMTP") as smtp:
        email_service.send_mail("a@b.c", "Hello", "<p>x</p>")
    server = smtp.return_value.__enter__.return_value
    server.starttls.assert_called_once()
    server.sendmail.assert_called_once()
    assert server.sendmail.call_args.args[1] == ["a@b.c"]


def test_admin_notice_escapes_user_input():
    subject, html = email_service.render_admin_notice(
        _applicant(full_name="<script>alert(1)</script>")
    )
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "newparent" in html and "np@example.com" in html
    assert "registration" in subject.lower()


def test_approved_email_links_to_frontend_login(smtp_on):
    _, html = email_service.render_approved(_applicant())
    assert "http://shop.test/login" in html


def test_rejected_email_contains_escaped_reason():
    _, html = email_service.render_rejected(
        _applicant(rejection_reason="Not a <b>valid</b> address")
    )
    assert "Not a &lt;b&gt;valid&lt;/b&gt; address" in html


def test_notify_returns_false_when_smtp_unset(monkeypatch, db):
    monkeypatch.setattr(settings, "smtp_host", "")
    assert registration_service.notify_approved(_applicant()) is False


def test_notify_returns_false_when_smtp_fails(smtp_on):
    with patch("app.services.email_service.smtplib.SMTP", side_effect=OSError("down")):
        assert registration_service.notify_rejected(_applicant(rejection_reason="nope nope")) is False


def test_admin_recipient_prefers_setting_then_first_admin(smtp_on, db, admin_user, monkeypatch):
    with patch("app.services.email_service.smtplib.SMTP") as smtp:
        assert registration_service.notify_admin_new_registration(db, _applicant()) is True
    assert smtp.return_value.__enter__.return_value.sendmail.call_args.args[1] == ["boss@test"]

    monkeypatch.setattr(settings, "admin_notify_email", "")
    with patch("app.services.email_service.smtplib.SMTP") as smtp:
        assert registration_service.notify_admin_new_registration(db, _applicant()) is True
    assert smtp.return_value.__enter__.return_value.sendmail.call_args.args[1] == [admin_user.email]


def test_admin_notice_skipped_when_no_recipient(smtp_on, db, monkeypatch):
    monkeypatch.setattr(settings, "admin_notify_email", "")
    assert registration_service.notify_admin_new_registration(db, _applicant()) is False


def test_notify_approved_never_raises_when_render_fails():
    with patch.object(email_service, "render_approved", side_effect=RuntimeError("boom")):
        assert registration_service.notify_approved(_applicant()) is False


def test_notify_admin_never_raises_when_recipient_lookup_fails():
    with patch.object(registration_service, "_admin_recipient", side_effect=RuntimeError("db down")):
        assert registration_service.notify_admin_new_registration(None, _applicant()) is False
