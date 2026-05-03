"""add stable task email submission key

Revision ID: 20260503_02
Revises: 20260503_01
Create Date: 2026-05-03 19:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260503_02"
down_revision = "20260503_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reimbursement_tasks",
        sa.Column("email_submission_key", sa.String(length=32), nullable=True),
    )
    op.execute(
        """
        UPDATE reimbursement_tasks
        SET email_submission_key = lower(substr(replace(id, '-', ''), 1, 8))
        WHERE email_submission_key IS NULL
        """
    )
    op.create_index(
        op.f("ix_reimbursement_tasks_email_submission_key"),
        "reimbursement_tasks",
        ["email_submission_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_reimbursement_tasks_email_submission_key"),
        table_name="reimbursement_tasks",
    )
    op.drop_column("reimbursement_tasks", "email_submission_key")
