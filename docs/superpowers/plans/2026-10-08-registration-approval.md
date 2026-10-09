# Registration Approval Flow and Chat Gating Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** New registrations wait for admin approval (with emails both ways), and the chat works only for logged-in, approved users.

**Architecture:** Add `approval_status` (`pending|approved|rejected`) plus `rejection_reason` and `reviewed_at` to `users`. Registration creates a `pending` user with no tokens. Login, token refresh and `get_current_user` accept only `approved` users. A new `registration_service` sends the three emails (best-effort, never failing the request) through a generic `email_service.send_mail`. Admin routes list/approve/reject pending registrations. The chat endpoint requires `get_current_user`, and the widget shows a popup when logged out.

**Tech Stack:** FastAPI, SQLAlchemy 2.x, Alembic (SQLite batch mode), pytest; React 18 + Vite + TypeScript + zustand + axios; Tailwind classes already in the repo.

**Spec:** `docs/superpowers/specs/2026-10-08-registration-approval-design.md`

## Global Constraints

- Money/pricing/checkout code is untouched.
- Existing and seeded users stay `approved`: model default `approved`, migration `server_default='approved'`. Only `/register` writes `pending`.
- Email failure never fails registration or an admin decision: commit first, then send, catch everything, report `email_sent`.
- Chat popup text, verbatim: `I am sorry I cannot respond to you till you register and log in. This is necessary to ensure that only validated people are allowed to use the Application & Chat.`
- Reject reason: required, trimmed, 5–500 characters.
- Error envelope via `api_error(status, code, message, field=None)`; new codes: `approval_pending` (403), `registration_rejected` (403), `already_reviewed` (409).
- New settings: `ADMIN_NOTIFY_EMAIL` (falls back to first admin user's email), `FRONTEND_BASE_URL` (default `http://localhost:5173`). `public_base_url` is the backend URL; do not use it for emailed login links.
- User-supplied text (full name, username, reason) is HTML-escaped in every email template.
- Code style: 2-space indent in TS, ES modules, `async/await`; Python follows the surrounding 4-space style. Comments only for non-obvious WHY.
- No new packages. No deploy or push. Commit through the `/commit` skill, never raw `git commit`.
- The user's global rule says to announce multi-file edits and to report after each step: state the file list at the start of each task.
- Backend commands run from `backend/`; frontend commands from `frontend/`. Never run `node --test` with a directory argument.

## Review Focus

- A user who was approved, got tokens, and is later set to `rejected` must lose access with the old access token and the old refresh token (tested in Task 3).
- A repeat Approve/Reject click, or Approve after Reject, must return 409 and not send a second email (Task 4).
- Reject with a whitespace-only or 4-character reason must be 422 and leave the user `pending` (Task 4).
- A name like `<script>alert(1)</script>` in a registration must be escaped in the admin email (Task 2).
- SMTP unset or failing: register, approve and reject still succeed with `email_sent: false` (Tasks 3, 4).
- Registering with a username that belongs to one row and an email that belongs to another row must give a clean 409, not a 500 (Task 3).
- A `rejected` user re-registering resets to `pending`, clears the reason, and a `pending`/`approved` duplicate still gets 409 (Task 3).
- Logout in the browser while the chat panel is open must close it and wipe the conversation, so the next person cannot read it (Task 8).

---

### Task 1: Data model, migration, settings, schema field

**Files:**
- Modify: `backend/app/models/user.py`
- Create: `backend/alembic/versions/0003_user_approval.py`
- Modify: `backend/app/core/config.py` (email block, after `email_from`)
- Modify: `backend/app/schemas/user.py` (`UserRead`, new schemas)
- Modify: `backend/.env.example`, root `.env.example` (email block)
- Test: `backend/tests/test_user_approval_model.py`

**Interfaces:**
- Produces: `ApprovalStatus(str, Enum)` in `app.models.user` with `PENDING="pending"`, `APPROVED="approved"`, `REJECTED="rejected"`; `User.approval_status`, `User.rejection_reason: str | None`, `User.reviewed_at: datetime | None`; `settings.admin_notify_email: str`, `settings.frontend_base_url: str`; `UserRead.approval_status: ApprovalStatus`; `RegisterResponse(status: str, message: str)`; `RegistrationRead(UserRead)` adding `rejection_reason: str | None`, `reviewed_at: datetime | None`; `RejectRequest(reason: str)`.

- [ ] **Step 1: Write the failing test**

```python
"""Approval columns on the User model and migration 0003."""

import sqlite3
import subprocess
import sys

from app.models.user import ApprovalStatus, User, UserRole
from app.schemas.user import UserRead


def test_new_user_defaults_to_approved(db):
    user = User(username="a", email="a@example.com", hashed_password="x", role=UserRole.CUSTOMER)
    db.add(user)
    db.commit()
    db.refresh(user)
    assert user.approval_status == ApprovalStatus.APPROVED
    assert user.rejection_reason is None
    assert user.reviewed_at is None
    assert UserRead.model_validate(user).approval_status == ApprovalStatus.APPROVED


def test_migration_0003_backfills_existing_users_as_approved(tmp_path):
    db_file = tmp_path / "mig.db"
    env = {"DATABASE_URL": f"sqlite:///{db_file}", "PATH": __import__("os").environ["PATH"]}
    run = lambda *args: subprocess.run(
        [sys.executable, "-m", "alembic", *args], env=env, check=True, capture_output=True
    )
    run("upgrade", "0002_guest_checkout")
    with sqlite3.connect(db_file) as conn:
        conn.execute(
            "INSERT INTO users (username, email, hashed_password, role, is_active, created_at, updated_at)"
            " VALUES ('old', 'old@example.com', 'x', 'customer', 1, '2026-01-01', '2026-01-01')"
        )
    run("upgrade", "head")
    with sqlite3.connect(db_file) as conn:
        row = conn.execute("SELECT approval_status FROM users WHERE username='old'").fetchone()
    assert row == ("approved",)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_user_approval_model.py -v`
Expected: FAIL with `ImportError: cannot import name 'ApprovalStatus'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/models/user.py` — add imports and enum, columns:

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, String
```

```python
class ApprovalStatus(str, enum.Enum):
    """Admin review state of a registration."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
```

Inside `User`, after `is_active`:

```python
    approval_status: Mapped[ApprovalStatus] = mapped_column(
        SAEnum(
            ApprovalStatus,
            native_enum=False,
            length=20,
            values_callable=lambda e: [m.value for m in e],
        ),
        default=ApprovalStatus.APPROVED,
        server_default=ApprovalStatus.APPROVED.value,
        nullable=False,
        index=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(500))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

`backend/alembic/versions/0003_user_approval.py`:

```python
"""Registration approval: approval_status, rejection_reason, reviewed_at on users.

Revision ID: 0003_user_approval
Revises: 0002_guest_checkout
Create Date: 2026-10-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_user_approval"
down_revision: Union[str, None] = "0002_guest_checkout"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default backfills every existing row as approved.
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "approval_status",
                sa.String(length=20),
                nullable=False,
                server_default="approved",
            )
        )
        batch_op.add_column(sa.Column("rejection_reason", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index("ix_users_approval_status", ["approval_status"])


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_approval_status")
        batch_op.drop_column("reviewed_at")
        batch_op.drop_column("rejection_reason")
        batch_op.drop_column("approval_status")
```

`backend/app/core/config.py`, after `email_from: str = ""`:

```python
    # Registration approval: who is told about new sign-ups, and the storefront
    # origin used for links in emails (public_base_url is the backend, not this).
    admin_notify_email: str = ""
    frontend_base_url: str = "http://localhost:5173"
```

`backend/app/schemas/user.py` — add import `Annotated`, `StringConstraints`; update `UserRead`, append new schemas:

```python
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

from app.models.user import ApprovalStatus, UserRole
```

In `UserRead` after `is_active: bool`: `approval_status: ApprovalStatus`

Append:

```python
class RegisterResponse(BaseModel):
    """Registration outcome: the account exists but cannot sign in yet."""

    status: str
    message: str


class RegistrationRead(UserRead):
    """A registration as the admin reviews it."""

    rejection_reason: str | None = None
    reviewed_at: datetime | None = None


class RejectRequest(BaseModel):
    """Admin rejection payload; the reason is emailed to the applicant."""

    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=500)]
```

Env examples — add to the email block of both `.env.example` files:

```
# Registration approval
ADMIN_NOTIFY_EMAIL=
FRONTEND_BASE_URL=http://localhost:5173
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_user_approval_model.py -v` then `python -m pytest -q`
Expected: new tests PASS; full suite still passes (model default keeps fixtures approved).

- [ ] **Step 5: Commit** via `/commit` — `feat: add registration approval columns and settings`

---

### Task 2: Email sending and templates

**Files:**
- Modify: `backend/app/services/email_service.py` (append; leave `send_receipt` untouched)
- Create: `backend/app/services/registration_service.py`
- Test: `backend/tests/test_registration_email.py`

**Interfaces:**
- Consumes: `settings.smtp_*`, `settings.email_from`, `settings.admin_notify_email`, `settings.frontend_base_url`, `User`, `UserRole`.
- Produces in `email_service`: `class EmailNotConfigured(RuntimeError)`; `send_mail(to: str, subject: str, html: str) -> None` (raises `EmailNotConfigured` when `smtp_host` is empty, raises smtplib errors otherwise); `render_admin_notice(user: User) -> tuple[str, str]`, `render_approved(user: User) -> tuple[str, str]`, `render_rejected(user: User) -> tuple[str, str]` each returning `(subject, html)`.
- Produces in `registration_service`: `notify_admin_new_registration(db: Session, user: User) -> bool`, `notify_approved(user: User) -> bool`, `notify_rejected(user: User) -> bool` — each returns True if sent, False on any failure (logged, never raises).

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_registration_email.py -v`
Expected: FAIL — `EmailNotConfigured` / `registration_service` not defined.

- [ ] **Step 3: Write the implementation**

Append to `backend/app/services/email_service.py` (add `from html import escape` and `from app.models.user import User` to the imports; keep the module docstring accurate by also mentioning registration emails):

```python
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
```

`backend/app/services/registration_service.py`:

```python
"""Best-effort emails for the registration approval flow.

Each function returns whether the email went out. They never raise: an email
problem must not undo a registration or an admin decision.
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User, UserRole
from app.services import email_service

logger = logging.getLogger(__name__)


def _admin_recipient(db: Session) -> str | None:
    if settings.admin_notify_email:
        return settings.admin_notify_email
    return db.execute(
        select(User.email).where(User.role == UserRole.ADMIN).order_by(User.id).limit(1)
    ).scalar_one_or_none()


def _send(to: str, subject_and_html: tuple[str, str], what: str) -> bool:
    subject, html = subject_and_html
    try:
        email_service.send_mail(to, subject, html)
        return True
    except Exception:
        logger.warning("Could not send %s email to %s", what, to, exc_info=True)
        return False


def notify_admin_new_registration(db: Session, user: User) -> bool:
    recipient = _admin_recipient(db)
    if recipient is None:
        logger.warning("No admin email available for new registration %s", user.username)
        return False
    return _send(recipient, email_service.render_admin_notice(user), "admin registration notice")


def notify_approved(user: User) -> bool:
    return _send(user.email, email_service.render_approved(user), "approval")


def notify_rejected(user: User) -> bool:
    return _send(user.email, email_service.render_rejected(user), "rejection")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_registration_email.py tests/test_email_service.py -v`
Expected: all PASS (existing receipt tests unchanged).

- [ ] **Step 5: Commit** via `/commit` — `feat: add registration emails and best-effort sender`

---

### Task 3: Register, login, refresh and token gating

**Files:**
- Modify: `backend/app/routers/auth.py` (`register`, `login`, `refresh`)
- Modify: `backend/app/core/deps.py` (`get_current_user`)
- Modify: `backend/tests/test_auth.py` (replace the first test)
- Test: `backend/tests/test_registration_flow.py`

**Interfaces:**
- Consumes: `ApprovalStatus`, `RegisterResponse`, `registration_service.notify_admin_new_registration(db, user) -> bool`.
- Produces: `POST /api/auth/register` → 201 `{status: "pending", message: str}`, no tokens; login errors `approval_pending` / `registration_rejected` (403); `get_current_user` and `/refresh` reject any non-`approved` user with 401.

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_auth.py`, replace `test_register_creates_customer_and_returns_tokens` with:

```python
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
```

`backend/tests/test_registration_flow.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_auth.py tests/test_registration_flow.py -v`
Expected: FAIL (register still returns tokens / `registration_service` not imported in router).

- [ ] **Step 3: Implement**

`backend/app/routers/auth.py` imports: add `ApprovalStatus` to the `app.models.user` import, `RegisterResponse` to the schemas import, `from app.services import registration_service`, and `from datetime import ...` already present.

Replace `register`:

```python
@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> RegisterResponse:
    """Create a pending customer account. An admin must approve it before sign-in."""
    matches = (
        db.execute(
            select(User).where(
                (User.username == payload.username) | (User.email == str(payload.email))
            )
        )
        .scalars()
        .all()
    )

    reapplying: User | None = None
    if len(matches) == 1 and matches[0].approval_status == ApprovalStatus.REJECTED:
        reapplying = matches[0]
    elif matches:
        field = "username" if matches[0].username == payload.username else "email"
        raise api_error(
            status.HTTP_409_CONFLICT,
            "already_registered",
            f"That {field} is already registered",
            field=field,
        )

    if reapplying is not None:
        user = reapplying
        user.username = payload.username
        user.email = str(payload.email)
        user.full_name = payload.full_name
        user.hashed_password = hash_password(payload.password)
        user.approval_status = ApprovalStatus.PENDING
        user.rejection_reason = None
        user.reviewed_at = None
    else:
        user = User(
            username=payload.username,
            email=str(payload.email),
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
            role=UserRole.CUSTOMER,
            approval_status=ApprovalStatus.PENDING,
        )
        db.add(user)
    db.commit()
    db.refresh(user)

    registration_service.notify_admin_new_registration(db, user)
    return RegisterResponse(
        status="pending",
        message="Your registration approval is in progress. You will get an email once it is reviewed.",
    )
```

In `login`, after the credentials check and before `is_active`:

```python
    if user.approval_status == ApprovalStatus.PENDING:
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            "approval_pending",
            "Your registration is awaiting admin approval. You will get an email once it is reviewed.",
        )
    if user.approval_status == ApprovalStatus.REJECTED:
        raise api_error(
            status.HTTP_403_FORBIDDEN,
            "registration_rejected",
            f"Your registration was not approved. Reason: {user.rejection_reason or 'not given'}",
        )
```

In `refresh`, change the user check to:

```python
    if user is None or not user.is_active or user.approval_status != ApprovalStatus.APPROVED:
```

`backend/app/core/deps.py`: import `ApprovalStatus` alongside `User, UserRole`; change the check in `get_current_user`:

```python
    if (
        user is None
        or not user.is_active
        or user.approval_status != ApprovalStatus.APPROVED
    ):
        raise _credentials_error("User account is unavailable")
```

`get_optional_user` is left as is (it is not a security gate; confirm with `grep -rn get_optional_user backend/app` that nothing uses it to authorize).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest -q`
Expected: all PASS. Chat tests are unaffected so far.

- [ ] **Step 5: Commit** via `/commit` — `feat: registrations start pending; login and tokens require approval`

---

### Task 4: Admin approvals API and stats

**Files:**
- Modify: `backend/app/routers/admin.py` (new section after `/users`; `/stats`)
- Test: `backend/tests/test_admin_registrations.py`

**Interfaces:**
- Consumes: `RegistrationRead`, `RejectRequest`, `ApprovalStatus`, `registration_service.notify_approved(user) -> bool`, `notify_rejected(user) -> bool`, `not_found` from `app.core.errors`.
- Produces: `GET /api/admin/registrations?status=pending|approved|rejected&page&page_size` → `Page[RegistrationRead]`; `POST /api/admin/registrations/{user_id}/approve` and `/reject` (body `{reason}`) → `{user: RegistrationRead, email_sent: bool}`; `/api/admin/stats` gains `pending_approvals: int`.

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_admin_registrations.py -v`
Expected: FAIL (404 on `/registrations`).

- [ ] **Step 3: Implement**

`backend/app/routers/admin.py` imports: `from datetime import datetime, timezone`; `from sqlalchemy import func, select, update`; `from app.models.user import ApprovalStatus, User`; `from app.schemas.user import RegistrationRead, RejectRequest, UserRead`; `from app.services import order_service, registration_service`.

Add after `admin_list_users`:

```python
# --------------------------------------------------------------------------
# Registration approvals
# --------------------------------------------------------------------------
class RegistrationDecision(BaseModel):
    """Outcome of an approve/reject click."""

    user: RegistrationRead
    email_sent: bool


@router.get("/registrations", response_model=Page[RegistrationRead])
def list_registrations(
    db: Session = Depends(get_db),
    status_filter: ApprovalStatus = Query(default=ApprovalStatus.PENDING, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[RegistrationRead]:
    """Registrations in one review state, oldest first."""
    base = select(User).where(User.approval_status == status_filter)
    total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
    rows = (
        db.execute(
            base.order_by(User.created_at, User.id).offset((page - 1) * page_size).limit(page_size)
        )
        .scalars()
        .all()
    )
    pages = (total + page_size - 1) // page_size if total else 0
    return Page[RegistrationRead](
        items=[RegistrationRead.model_validate(user) for user in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


def _decide(db: Session, user_id: int, new_status: ApprovalStatus, reason: str | None) -> User:
    """Move a pending registration to a final state; 409 if it was already reviewed."""
    if db.get(User, user_id) is None:
        raise not_found("Registration")
    # Single conditional UPDATE: two admins clicking at once cannot both win.
    result = db.execute(
        update(User)
        .where(User.id == user_id, User.approval_status == ApprovalStatus.PENDING)
        .values(
            approval_status=new_status,
            rejection_reason=reason,
            reviewed_at=datetime.now(timezone.utc),
        )
    )
    if result.rowcount != 1:
        db.rollback()
        raise api_error(
            status.HTTP_409_CONFLICT,
            "already_reviewed",
            "This registration has already been reviewed",
        )
    db.commit()
    user = db.get(User, user_id)
    db.refresh(user)
    return user


@router.post("/registrations/{user_id}/approve", response_model=RegistrationDecision)
def approve_registration(user_id: int, db: Session = Depends(get_db)) -> RegistrationDecision:
    user = _decide(db, user_id, ApprovalStatus.APPROVED, None)
    email_sent = registration_service.notify_approved(user)
    return RegistrationDecision(user=RegistrationRead.model_validate(user), email_sent=email_sent)


@router.post("/registrations/{user_id}/reject", response_model=RegistrationDecision)
def reject_registration(
    user_id: int, payload: RejectRequest, db: Session = Depends(get_db)
) -> RegistrationDecision:
    user = _decide(db, user_id, ApprovalStatus.REJECTED, payload.reason)
    email_sent = registration_service.notify_rejected(user)
    return RegistrationDecision(user=RegistrationRead.model_validate(user), email_sent=email_sent)
```

Add `from pydantic import BaseModel` to the imports. In `admin_stats`, add to the returned dict:

```python
        "pending_approvals": db.execute(
            select(func.count(User.id)).where(User.approval_status == ApprovalStatus.PENDING)
        ).scalar_one(),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_admin_registrations.py tests/test_admin_access.py -v` then `python -m pytest -q`
Expected: all PASS.

- [ ] **Step 5: Commit** via `/commit` — `feat: admin API to approve and reject registrations`

---

### Task 5: Chat requires a signed-in user

**Files:**
- Modify: `backend/app/routers/chat.py`
- Modify: `backend/tests/test_chat.py` (autouse sign-in fixture + new tests)

**Interfaces:**
- Consumes: `get_current_user` from `app.core.deps`.
- Produces: `POST /api/chat` returns 401 `not_authenticated` without a valid approved-user token.

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_chat.py` add after `_configured`:

```python
from tests.conftest import auth_headers


@pytest.fixture(autouse=True)
def _signed_in(client, customer_user):
    """Chat needs a signed-in user; individual tests drop the header to test the gate."""
    client.headers.update(auth_headers(client, "shopper", "Customer123!"))
```

and tests:

```python
def test_chat_requires_login(client, monkeypatch):
    async def boom(message, session_id):
        raise AssertionError("Lyzr must not be called")

    monkeypatch.setattr(chat_service, "ask_agent", boom)
    client.headers.pop("Authorization")
    response = client.post("/api/chat", json=VALID)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_chat_rejects_a_garbage_token(client):
    client.headers["Authorization"] = "Bearer not-a-token"
    assert client.post("/api/chat", json=VALID).status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_chat.py -v`
Expected: `test_chat_requires_login` FAILS (200 instead of 401).

- [ ] **Step 3: Implement**

`backend/app/routers/chat.py`: update the module docstring to `"""Shopper chatbot endpoint. Requires a signed-in, approved user."""`, add imports `from app.core.deps import get_current_user` and `from app.models.user import User`, and change the handler signature:

```python
@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> ChatResponse:
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest -q`
Expected: full backend suite PASS.

- [ ] **Step 5: Commit** via `/commit` — `feat: chat endpoint requires a signed-in approved user`

---

### Task 6: Frontend auth plumbing, register popup, login messages, shared Dialog

**Files:**
- Create: `frontend/src/components/Dialog.tsx`
- Modify: `frontend/src/types.ts` (`User`, `AdminStats`, new types)
- Modify: `frontend/src/api/auth.ts`
- Modify: `frontend/src/store/authStore.ts`
- Modify: `frontend/src/pages/RegisterPage.tsx`
- Modify: `frontend/src/pages/LoginPage.tsx` (no code change needed if `toApiError(...).message` already carries the server text — verify in Step 4 and leave the file alone if so)

**Interfaces:**
- Produces: `Dialog` component props `{ title: string; onClose: () => void; children: ReactNode; actions: ReactNode }` (renders `role="dialog"` overlay, closes on Escape); types `ApprovalStatus = 'pending' | 'approved' | 'rejected'`, `RegisterResult { status: string; message: string }`; `User.approval_status: ApprovalStatus`; `AdminStats.pending_approvals: number`; `authApi.register(payload): Promise<RegisterResult>`; store `register(payload): Promise<RegisterResult>` (does not touch tokens or `user`).

- [ ] **Step 1: Types and API**

`frontend/src/types.ts`: add `export type ApprovalStatus = 'pending' | 'approved' | 'rejected'`; add `approval_status: ApprovalStatus` to `User`; add `pending_approvals: number` to `AdminStats`; add:

```ts
export interface RegisterResult {
  status: string
  message: string
}

export interface Registration extends User {
  rejection_reason: string | null
  reviewed_at: string | null
}

export interface RegistrationDecision {
  user: Registration
  email_sent: boolean
}
```

`frontend/src/api/auth.ts`: import `RegisterResult`; change register:

```ts
  async register(payload: RegisterPayload): Promise<RegisterResult> {
    const { data } = await api.post<RegisterResult>('/auth/register', payload)
    return data
  },
```

`frontend/src/store/authStore.ts`: import `RegisterResult` from `'../types'`; change the interface line to `register: (payload: RegisterPayload) => Promise<RegisterResult>` and the implementation:

```ts
  async register(payload) {
    set({ loading: true })
    try {
      // The account is pending: no tokens, no sign-in.
      return await authApi.register(payload)
    } finally {
      set({ loading: false })
    }
  },
```

- [ ] **Step 2: Dialog component**

`frontend/src/components/Dialog.tsx`:

```tsx
import { type ReactNode, useEffect, useRef } from 'react'

interface DialogProps {
  title: string
  onClose: () => void
  children: ReactNode
  actions: ReactNode
}

/** Centered modal. Escape and a click on the backdrop both call onClose. */
export default function Dialog({ title, onClose, children, actions }: DialogProps) {
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    panelRef.current?.focus()
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-[60] grid place-items-center bg-ink-900/50 p-4"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        tabIndex={-1}
        className="card w-full max-w-md p-6 focus:outline-none"
      >
        <h2 id="dialog-title" className="font-display text-xl text-ink-900">
          {title}
        </h2>
        <div className="mt-3 text-base text-ink-700">{children}</div>
        <div className="mt-6 flex justify-end gap-2">{actions}</div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Register popup**

`RegisterPage.tsx`: drop the `useCartStore`/`mergeGuestCart` use (no session yet, nothing to merge), add `Dialog` import and `const [submitted, setSubmitted] = useState(false)`. Replace the try body in `handleSubmit`:

```tsx
    try {
      await register({
        username: form.username.trim(),
        email: form.email.trim(),
        full_name: form.full_name.trim() || undefined,
        password: form.password,
      })
      setSubmitted(true)
    } catch (caught) {
      setError(toApiError(caught).message)
    }
```

After `</form>` inside `SplitPage` add:

```tsx
      {submitted && (
        <Dialog
          title="Registration submitted"
          onClose={() => navigate('/login', { replace: true })}
          actions={
            <button type="button" className="btn-primary px-5 py-2" onClick={() => navigate('/login', { replace: true })}>
              OK
            </button>
          }
        >
          Your registration approval is in progress. We have asked the site admin to review it,
          and you will get an email as soon as a decision is made. You can sign in once it is approved.
        </Dialog>
      )}
```

- [ ] **Step 4: Verify**

Run (from `frontend/`): `npm run typecheck`
Expected: no errors (any other file using `AuthResponse` from register will surface here — fix only those).
Then confirm `LoginPage.tsx` needs no change: `toApiError(caught).message` already shows the server's `approval_pending` / `registration_rejected` text. If so, leave it.

- [ ] **Step 5: Commit** via `/commit` — `feat: register shows pending popup; no auto sign-in`

---

### Task 7: Admin Approvals page, tab badge, overview card

**Files:**
- Modify: `frontend/src/api/admin.ts`
- Create: `frontend/src/pages/admin/AdminApprovalsPage.tsx`
- Modify: `frontend/src/App.tsx` (route)
- Modify: `frontend/src/components/AdminLayout.tsx` (tab + badge)
- Modify: `frontend/src/pages/admin/AdminOverviewPage.tsx` (pending card)

**Interfaces:**
- Consumes: `Registration`, `RegistrationDecision`, `Paged`, `Dialog`, `formatDate`.
- Produces: `adminApi.registrations(page?: number, pageSize?: number): Promise<Paged<Registration>>` (pending only), `adminApi.approveRegistration(id: number): Promise<RegistrationDecision>`, `adminApi.rejectRegistration(id: number, reason: string): Promise<RegistrationDecision>`; route `/admin/approvals`.

- [ ] **Step 1: API client** — add to `adminApi` (and import `Registration`, `RegistrationDecision` types):

```ts
  async registrations(page = 1, pageSize = 20): Promise<Paged<Registration>> {
    const { data } = await api.get<Paged<Registration>>('/admin/registrations', {
      params: { status: 'pending', page, page_size: pageSize },
    })
    return data
  },
  async approveRegistration(id: number): Promise<RegistrationDecision> {
    const { data } = await api.post<RegistrationDecision>(`/admin/registrations/${id}/approve`)
    return data
  },
  async rejectRegistration(id: number, reason: string): Promise<RegistrationDecision> {
    const { data } = await api.post<RegistrationDecision>(`/admin/registrations/${id}/reject`, {
      reason,
    })
    return data
  },
```

- [ ] **Step 2: Approvals page** — `AdminApprovalsPage.tsx`:

```tsx
import { useCallback, useEffect, useState } from 'react'

import { adminApi } from '../../api/admin'
import { toApiError } from '../../api/client'
import Dialog from '../../components/Dialog'
import ErrorBanner from '../../components/ErrorBanner'
import Spinner from '../../components/Spinner'
import { formatDate } from '../../lib/format'
import type { Registration } from '../../types'

/** Pending registrations with Approve / Reject (reason required). */
export default function AdminApprovalsPage() {
  const [items, setItems] = useState<Registration[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [rejecting, setRejecting] = useState<Registration | null>(null)
  const [reason, setReason] = useState('')

  const load = useCallback(async () => {
    try {
      setItems((await adminApi.registrations(1, 100)).items)
    } catch (caught) {
      setError(toApiError(caught).message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  function report(name: string, verb: string, emailSent: boolean) {
    setNotice(
      emailSent
        ? `${name} ${verb}. The applicant was emailed.`
        : `${name} ${verb}, but the email could not be sent. Please contact them directly.`,
    )
  }

  async function approve(user: Registration) {
    setBusyId(user.id)
    setError(null)
    try {
      const result = await adminApi.approveRegistration(user.id)
      report(user.username, 'approved', result.email_sent)
    } catch (caught) {
      setError(toApiError(caught).message)
    } finally {
      setBusyId(null)
      await load()
    }
  }

  async function confirmReject() {
    if (!rejecting) return
    const target = rejecting
    setBusyId(target.id)
    setError(null)
    try {
      const result = await adminApi.rejectRegistration(target.id, reason.trim())
      report(target.username, 'rejected', result.email_sent)
      setRejecting(null)
      setReason('')
    } catch (caught) {
      setError(toApiError(caught).message)
    } finally {
      setBusyId(null)
      await load()
    }
  }

  if (loading) return <Spinner label="Loading registrations…" />

  const reasonTooShort = reason.trim().length < 5

  return (
    <div className="space-y-4">
      <ErrorBanner message={error} onDismiss={() => setError(null)} />
      {notice && (
        <p role="status" className="rounded-lg bg-green-50 px-4 py-3 text-sm text-green-800">
          {notice}
        </p>
      )}

      {items.length === 0 ? (
        <p className="card p-6 text-ink-700">No registrations are waiting for approval.</p>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-ink-800/10 text-xs uppercase tracking-wide text-ink-700">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Username</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Requested</th>
                <th className="px-4 py-3 text-right">Decision</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-800/5">
              {items.map((user) => (
                <tr key={user.id}>
                  <td className="px-4 py-3 font-medium">{user.full_name ?? '—'}</td>
                  <td className="px-4 py-3">{user.username}</td>
                  <td className="px-4 py-3">{user.email}</td>
                  <td className="px-4 py-3 text-ink-700">{formatDate(user.created_at)}</td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-2">
                      <button
                        type="button"
                        className="btn-primary px-3 py-1.5 text-sm"
                        disabled={busyId === user.id}
                        onClick={() => void approve(user)}
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        className="rounded-lg px-3 py-1.5 text-sm font-semibold text-red-700 ring-1 ring-red-300 hover:bg-red-50 disabled:opacity-50"
                        disabled={busyId === user.id}
                        onClick={() => {
                          setReason('')
                          setRejecting(user)
                        }}
                      >
                        Reject
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {rejecting && (
        <Dialog
          title={`Reject ${rejecting.username}?`}
          onClose={() => setRejecting(null)}
          actions={
            <>
              <button
                type="button"
                className="rounded-lg px-3 py-2 text-sm font-medium text-ink-700 hover:bg-orange-100"
                onClick={() => setRejecting(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded-lg bg-red-600 px-3 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50"
                disabled={reasonTooShort || busyId === rejecting.id}
                onClick={() => void confirmReject()}
              >
                Reject and email
              </button>
            </>
          }
        >
          <label className="label" htmlFor="reject-reason">
            Reason (emailed to the applicant, 5–500 characters)
          </label>
          <textarea
            id="reject-reason"
            className="input mt-1 h-28 w-full"
            maxLength={500}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </Dialog>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Route, tab with badge, overview card**

`App.tsx`: `import AdminApprovalsPage from './pages/admin/AdminApprovalsPage'` and inside the admin route add `<Route path="approvals" element={<AdminApprovalsPage />} />`.

`AdminLayout.tsx`: add `{ to: '/admin/approvals', label: 'Approvals' }` to `TABS` (place it second). Add the badge: import `useEffect, useState` and `adminApi`; inside the component:

```tsx
  const [pending, setPending] = useState(0)
  const location = useLocation()

  useEffect(() => {
    adminApi.stats().then((stats) => setPending(stats.pending_approvals)).catch(() => {})
  }, [location.pathname])
```

(import `useLocation` from `react-router-dom`). In the tab render, after `{tab.label}` add:

```tsx
            {tab.to === '/admin/approvals' && pending > 0 && (
              <span className="ml-2 rounded-full bg-red-600 px-2 py-0.5 text-xs font-bold text-white">
                {pending}
              </span>
            )}
```

The badge refetches on each admin navigation, so it drops after a decision once the admin moves tabs. Approve/reject on the page itself does not refresh it until navigation. If that feels stale, that is acceptable for this scope.

`AdminOverviewPage.tsx`: above the tiles grid, inside the root `div`, add (shown only when `stats && stats.pending_approvals > 0`):

```tsx
      {stats && stats.pending_approvals > 0 && (
        <Link
          to="/admin/approvals"
          className="card flex items-center justify-between border-l-4 border-red-500 p-5 hover:bg-orange-50"
        >
          <span className="font-display text-lg text-ink-900">
            {stats.pending_approvals} registration{stats.pending_approvals === 1 ? '' : 's'} waiting for approval
          </span>
          <span className="text-sm font-semibold text-brand-700">Review →</span>
        </Link>
      )}
```

- [ ] **Step 4: Verify**

Run (from `frontend/`): `npm run typecheck`
Expected: no errors.

- [ ] **Step 5: Commit** via `/commit` — `feat: admin approvals page, badge and overview card`

---

### Task 8: Chat login gate in the widget

**Files:**
- Create: `frontend/src/components/chat/chatGate.ts`
- Modify: `frontend/src/components/ChatWidget.tsx`
- Test: `frontend/tests/chatGate.test.mjs`

**Interfaces:**
- Consumes: `useAuthStore`, `Dialog`.
- Produces: `CHAT_LOGIN_REQUIRED_MESSAGE: string` (the exact required text) in `chatGate.ts`.

- [ ] **Step 1: Write the failing test** — `frontend/tests/chatGate.test.mjs`:

```js
import assert from 'node:assert/strict'
import test from 'node:test'

import { CHAT_LOGIN_REQUIRED_MESSAGE } from '../src/components/chat/chatGate.ts'

test('the logged-out chat popup says exactly what was requested', () => {
  assert.equal(
    CHAT_LOGIN_REQUIRED_MESSAGE,
    'I am sorry I cannot respond to you till you register and log in. This is necessary to ensure that only validated people are allowed to use the Application & Chat.',
  )
})
```

- [ ] **Step 2: Run to verify it fails**

Run (from `frontend/`): `node --test`
Expected: FAIL — cannot find module `chatGate.ts`.

- [ ] **Step 3: Implement**

`frontend/src/components/chat/chatGate.ts`:

```ts
export const CHAT_LOGIN_REQUIRED_MESSAGE =
  'I am sorry I cannot respond to you till you register and log in. This is necessary to ensure that only validated people are allowed to use the Application & Chat.'
```

`ChatWidget.tsx` edits:
- Imports: `import { Link } from 'react-router-dom'` (extend the existing `useLocation` import), `import { useAuthStore } from '../store/authStore'`, `import Dialog from './Dialog'`, `import { CHAT_LOGIN_REQUIRED_MESSAGE } from './chat/chatGate'`.
- With the other hooks (before the `/admin` early return at line 128):

```tsx
  const user = useAuthStore((state) => state.user)
  const [gateOpen, setGateOpen] = useState(false)
```

- Add an effect after the existing effects, also before the early return. It runs when the signed-in person changes, closing the panel and wiping the conversation so the next person cannot read it:

```tsx
  const userId = user?.id ?? null
  useEffect(() => {
    chatGeneration.current += 1
    inFlight.current = false
    sessionId.current = null
    setOpen(false)
    setMessages([greeting()])
    setDraft('')
    setError(null)
    setPending(false)
    try {
      localStorage.removeItem(SESSION_KEY)
    } catch {
      // Storage blocked: nothing persisted to clear.
    }
  }, [userId])
```

- Add after `newChat`:

```tsx
  function openChat() {
    if (!user) {
      setGateOpen(true)
      return
    }
    setOpen(true)
  }
```

- Replace the pill's `onClick={() => setOpen(true)}` with `onClick={openChat}`, and the launcher's `onClick={() => setOpen((current) => !current)}` with `onClick={() => (open ? setOpen(false) : openChat())}`.
- At the end of the root `div` (just before its closing tag) add:

```tsx
      {gateOpen && (
        <Dialog
          title="Please log in to chat"
          onClose={() => setGateOpen(false)}
          actions={
            <>
              <Link
                to="/register"
                onClick={() => setGateOpen(false)}
                className="rounded-lg px-3 py-2 text-sm font-medium text-ink-700 hover:bg-orange-100"
              >
                Register
              </Link>
              <Link
                to="/login"
                onClick={() => setGateOpen(false)}
                className="btn-primary px-4 py-2 text-sm"
              >
                Log in
              </Link>
            </>
          }
        >
          {CHAT_LOGIN_REQUIRED_MESSAGE}
        </Dialog>
      )}
```

Note: the effect runs once on mount too, which is harmless (fresh greeting, no stored session). Because `localStorage.removeItem(SESSION_KEY)` runs on every user change, each login starts a fresh Lyzr session.

- [ ] **Step 4: Verify**

Run (from `frontend/`): `node --test` and `npm run typecheck`
Expected: all node tests pass (including the new one); typecheck clean.

- [ ] **Step 5: Commit** via `/commit` — `feat: chat popup for logged-out visitors; reset chat on user change`

---

### Task 9: End-to-end check and docs

**Files:**
- Modify: `CLAUDE.md` (Chatbot and Auth sections), `README.md` (auth/API table if it lists register or chat), `backend/.env` is **not** touched (secrets stay out of the repo; tell the user which two vars to set).

**Interfaces:** none.

- [ ] **Step 1: Apply the migration to the dev DB.** Before running it, copy `backend/app.db` to a throwaway backup outside the repo (`backend/app.db.bak` already exists untracked, so use a different name or location). Run from `backend/`: `alembic current`, then `alembic upgrade head`, then `alembic current`.
Expected: current revision becomes `0003_user_approval (head)`.

- [ ] **Step 2: Run both suites.** `python -m pytest -q` (backend) and `node --test` + `npm run typecheck` (frontend). Expected: all green.

- [ ] **Step 3: Browser walkthrough** (start with `.\scripts\start.ps1`; SMTP may be unset, in which case the admin notice and approvals show `email_sent: false` and the backend log shows the warning — that is the expected degraded path). Verify each of:
  1. Logged out, click the chat launcher → popup shows the exact message; the panel does not open.
  2. Register a new user → "Registration submitted" popup → OK lands on `/login`.
  3. Log in as that user → blocked with the "awaiting admin approval" message.
  4. Log in as `admin` / `Admin123!` → Overview shows the "1 registration waiting" card; the Approvals tab shows a badge of 1.
  5. Reject with a 2-character reason → button disabled; with a real reason → row disappears; log in as the user → rejected message with the reason.
  6. Re-register the same username → popup again; admin sees it pending again; approve → user can log in and the chat opens and answers.
  7. Log out while the chat is open → panel closes; log in as another user → chat starts empty.
  Report what you saw for each item, including any that failed.

- [ ] **Step 4: Docs.** In `CLAUDE.md`: change the Chatbot paragraph's "public no-auth endpoint" to "requires a signed-in, approved user (`get_current_user`); 401 otherwise", add the widget gate/popup and per-user reset, and add a short "Registration approval" subsection to Auth (statuses, login error codes `approval_pending` / `registration_rejected`, admin routes, `ADMIN_NOTIFY_EMAIL` / `FRONTEND_BASE_URL`, best-effort email, migration `0003_user_approval`). Update the `README.md` API table rows for `/auth/register`, `/chat` and the new `/admin/registrations*` routes if the table lists them.

- [ ] **Step 5: Tell the user** to set `ADMIN_NOTIFY_EMAIL` and `FRONTEND_BASE_URL` (plus the existing `SMTP_*`) in `backend/.env` and in the Render dashboard before deploying, then commit via `/commit` — `docs: registration approval and chat gating`

---

## Self-Review

- **Spec coverage:** data (T1), register + re-apply + admin email (T2, T3), login/refresh/deps gating (T3), admin routes + stats + emails + settings (T1, T2, T4), register popup (T6), login messages (T3 server text, T6 verification), admin Approvals tab/badge/overview card/reject modal (T7), chat popup + server-side 401 + per-user reset (T5, T8), tests and verification (each task, T9). Out-of-scope items (email one-click links, bulk actions) are not planned.
- **Placeholders:** none; every code step shows the code.
- **Type consistency:** `ApprovalStatus`, `RegisterResponse`/`RegisterResult`, `RegistrationRead`/`Registration`, `RegistrationDecision` (`user`, `email_sent`), `notify_*` signatures, and `pending_approvals` are used with the same names across backend and frontend tasks. The patch targets in tests (`app.routers.auth.registration_service...`, `app.routers.admin.registration_service...`) match the `from app.services import registration_service` imports.
- **Known limits:** no frontend unit tests beyond the exact-message test (the repo has no component test setup); the admin badge refreshes on navigation, not instantly after a decision.
