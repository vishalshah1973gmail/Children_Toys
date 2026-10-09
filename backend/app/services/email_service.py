"""Registration emails, sent over real SMTP (Gmail + app password).

send_mail raises on any failure; services/registration_service.py sends
best-effort and logs instead of failing the request.
"""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

from app.core.config import settings
from app.models.user import User


class EmailNotConfigured(RuntimeError):
    """SMTP settings are empty, so nothing can be sent."""


def send_mail(to: str, subject: str, html: str) -> None:
    """Send one HTML email. Raises EmailNotConfigured or an smtplib/OSError on failure."""
    if not settings.smtp_host:
        raise EmailNotConfigured("SMTP_HOST is not set")
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = settings.email_from or settings.smtp_user
    message["To"] = to
    message.attach(MIMEText(html, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_app_password)
        server.sendmail(message["From"], [to], message.as_string())


def _display_name(user: User) -> str:
    return escape(user.full_name or user.username)


def render_admin_notice(user: User) -> tuple[str, str]:
    """Tell the admin someone is waiting for approval."""
    portal = f"{settings.frontend_base_url}/admin/approvals"
    html = (
        "<h2>New registration awaiting approval</h2>"
        f"<p><strong>Name:</strong> {escape(user.full_name or '-')}<br>"
        f"<strong>Username:</strong> {escape(user.username)}<br>"
        f"<strong>Email:</strong> {escape(user.email)}</p>"
        f"<p>Log in to the Admin Portal and approve or reject this request: "
        f"<a href='{portal}'>{portal}</a></p>"
    )
    return f"New registration request: {user.username}", html


def render_approved(user: User) -> tuple[str, str]:
    """Welcome email with the login link."""
    login_url = f"{settings.frontend_base_url}/login"
    html = (
        f"<h2>Welcome to ToyBox, {_display_name(user)}!</h2>"
        "<p>Your registration has been approved. You can now sign in with the "
        "username and password you chose.</p>"
        f"<p><a href='{login_url}'>{login_url}</a></p>"
    )
    return "Your ToyBox registration is approved", html


def render_rejected(user: User) -> tuple[str, str]:
    """Rejection email carrying the admin's reason."""
    html = (
        f"<h2>Hello {_display_name(user)},</h2>"
        "<p>Your ToyBox registration was not approved.</p>"
        f"<p><strong>Reason:</strong> {escape(user.rejection_reason or '')}</p>"
        "<p>You will not be able to sign in with this account.</p>"
    )
    return "Your ToyBox registration was not approved", html
