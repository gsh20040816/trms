"""add invoice corporate transfer reference

Revision ID: 20260501_01
Revises: 20260430_01
Create Date: 2026-05-01 23:35:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260501_01"
down_revision = "20260430_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column("corporate_transfer_reference", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("invoices", "corporate_transfer_reference")
