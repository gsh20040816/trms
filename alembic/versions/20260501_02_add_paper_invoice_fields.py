"""add paper invoice fields

Revision ID: 20260501_02
Revises: 20260501_01
Create Date: 2026-05-02 00:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260501_02"
down_revision = "20260501_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column("is_paper_invoice", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "invoices",
        sa.Column("paper_invoice_received", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "invoices",
        sa.Column("paper_invoice_received_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column("paper_invoice_received_by", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_invoices_paper_invoice_received_by",
        "invoices",
        ["paper_invoice_received_by"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_invoices_paper_invoice_received_by", table_name="invoices")
    op.drop_column("invoices", "paper_invoice_received_by")
    op.drop_column("invoices", "paper_invoice_received_at")
    op.drop_column("invoices", "paper_invoice_received")
    op.drop_column("invoices", "is_paper_invoice")
