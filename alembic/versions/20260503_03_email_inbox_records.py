"""add email inbox records

Revision ID: 20260503_03
Revises: 20260503_02
Create Date: 2026-05-03 21:15:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260503_03"
down_revision = "20260503_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_inbox_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("mailbox_uid", sa.String(length=255), nullable=False),
        sa.Column("message_id", sa.String(length=255), nullable=True),
        sa.Column("sender_email", sa.String(length=320), nullable=False),
        sa.Column("subject", sa.String(length=998), nullable=False),
        sa.Column("raw_storage_key", sa.String(length=512), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("result_code", sa.String(length=64), nullable=True),
        sa.Column("resolved_member_id", sa.String(length=128), nullable=True),
        sa.Column("submitted_task_key", sa.String(length=64), nullable=True),
        sa.Column("resolved_task_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_email_inbox_records_mailbox_uid"),
        "email_inbox_records",
        ["mailbox_uid"],
        unique=True,
    )
    op.create_index(
        op.f("ix_email_inbox_records_message_id"),
        "email_inbox_records",
        ["message_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_email_inbox_records_sender_email"),
        "email_inbox_records",
        ["sender_email"],
        unique=False,
    )
    op.create_index(
        op.f("ix_email_inbox_records_status"),
        "email_inbox_records",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_email_inbox_records_resolved_member_id"),
        "email_inbox_records",
        ["resolved_member_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_email_inbox_records_submitted_task_key"),
        "email_inbox_records",
        ["submitted_task_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_email_inbox_records_resolved_task_id"),
        "email_inbox_records",
        ["resolved_task_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_email_inbox_records_resolved_task_id"), table_name="email_inbox_records")
    op.drop_index(op.f("ix_email_inbox_records_submitted_task_key"), table_name="email_inbox_records")
    op.drop_index(op.f("ix_email_inbox_records_resolved_member_id"), table_name="email_inbox_records")
    op.drop_index(op.f("ix_email_inbox_records_status"), table_name="email_inbox_records")
    op.drop_index(op.f("ix_email_inbox_records_sender_email"), table_name="email_inbox_records")
    op.drop_index(op.f("ix_email_inbox_records_message_id"), table_name="email_inbox_records")
    op.drop_index(op.f("ix_email_inbox_records_mailbox_uid"), table_name="email_inbox_records")
    op.drop_table("email_inbox_records")
