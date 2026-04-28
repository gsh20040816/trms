"""add auth registration audit fields

Revision ID: 20260428_02
Revises: 20260428_01
Create Date: 2026-04-28 15:35:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260428_02"
down_revision = "20260428_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_accounts",
        sa.Column(
            "registration_source",
            sa.String(length=32),
            nullable=False,
            server_default="self_service",
        ),
    )
    op.add_column(
        "user_accounts",
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_accounts", "created_by_user_id")
    op.drop_column("user_accounts", "registration_source")
