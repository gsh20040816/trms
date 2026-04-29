"""add invoice member submission status

Revision ID: 20260430_01
Revises: 20260429_02
Create Date: 2026-04-30 02:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260430_01"
down_revision = "20260429_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column(
            "member_submission_status",
            sa.String(length=32),
            nullable=False,
            server_default="unsubmitted",
        ),
    )
    op.add_column(
        "invoices",
        sa.Column("submitted_by_member_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_invoices_member_submission_status",
        "invoices",
        ["member_submission_status"],
    )
    op.create_index(
        "ix_invoices_submitted_by_member_id",
        "invoices",
        ["submitted_by_member_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_invoices_submitted_by_member_id", table_name="invoices")
    op.drop_index("ix_invoices_member_submission_status", table_name="invoices")
    op.drop_column("invoices", "submitted_at")
    op.drop_column("invoices", "submitted_by_member_id")
    op.drop_column("invoices", "member_submission_status")
