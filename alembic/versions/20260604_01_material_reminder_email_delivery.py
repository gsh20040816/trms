"""add email delivery fields to material reminders

Revision ID: 20260604_01
Revises: 20260504_01
Create Date: 2026-06-04 10:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_01"
down_revision = "20260504_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "material_reminders",
        sa.Column("email_recipient", sa.String(length=320), nullable=True),
    )
    op.add_column(
        "material_reminders",
        sa.Column("email_subject", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "material_reminders",
        sa.Column("email_body", sa.String(length=8000), nullable=True),
    )
    op.add_column(
        "material_reminders",
        sa.Column("email_delivery_status", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "material_reminders",
        sa.Column("email_failure_reason", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "material_reminders",
        sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("material_reminders", "email_sent_at")
    op.drop_column("material_reminders", "email_failure_reason")
    op.drop_column("material_reminders", "email_delivery_status")
    op.drop_column("material_reminders", "email_body")
    op.drop_column("material_reminders", "email_subject")
    op.drop_column("material_reminders", "email_recipient")
