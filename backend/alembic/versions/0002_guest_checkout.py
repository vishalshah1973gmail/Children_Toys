"""Guest checkout: nullable order.user_id, billing columns, card summary on payments.

Revision ID: 0002_guest_checkout
Revises: 0001_initial
Create Date: 2026-09-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_guest_checkout"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=True)
        batch_op.add_column(sa.Column("billing_name", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("billing_line1", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("billing_line2", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("billing_city", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("billing_state", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("billing_postal_code", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("billing_country", sa.String(length=2), nullable=True))

    op.add_column("payments", sa.Column("card_brand", sa.String(length=20), nullable=True))
    op.add_column("payments", sa.Column("card_last4", sa.String(length=4), nullable=True))
    op.add_column("payments", sa.Column("card_exp_month", sa.Integer(), nullable=True))
    op.add_column("payments", sa.Column("card_exp_year", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("payments", "card_exp_year")
    op.drop_column("payments", "card_exp_month")
    op.drop_column("payments", "card_last4")
    op.drop_column("payments", "card_brand")

    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_column("billing_country")
        batch_op.drop_column("billing_postal_code")
        batch_op.drop_column("billing_state")
        batch_op.drop_column("billing_city")
        batch_op.drop_column("billing_line2")
        batch_op.drop_column("billing_line1")
        batch_op.drop_column("billing_name")
        batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
