"""lab4 analytics features

Revision ID: 20260520_02
Revises: 20260421_01
Create Date: 2026-05-20 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260520_02"
down_revision = "20260421_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("processed_events") as batch_op:
        batch_op.add_column(sa.Column("category", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("duration_seconds", sa.Float(), nullable=True))

    op.create_table(
        "follower_counts",
        sa.Column("user_id", sa.Integer(), primary_key=True),
        sa.Column("followers_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("follower_counts")
    with op.batch_alter_table("processed_events") as batch_op:
        batch_op.drop_column("duration_seconds")
        batch_op.drop_column("category")
