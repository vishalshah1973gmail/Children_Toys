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
