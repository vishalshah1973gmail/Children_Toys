"""Approval columns on the User model and migration 0003."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from app.models.user import ApprovalStatus, User, UserRole
from app.schemas.user import UserRead

BACKEND_DIR = Path(__file__).resolve().parent.parent


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
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db_file}"}
    run = lambda *args: subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        env=env,
        cwd=BACKEND_DIR,
        check=True,
        capture_output=True,
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
