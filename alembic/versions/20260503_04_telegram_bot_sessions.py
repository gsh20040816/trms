"""add telegram bot binding authorizations and task contexts

Revision ID: 20260503_04
Revises: 20260503_03
Create Date: 2026-05-03 23:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260503_04"
down_revision = "20260503_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telegram_binding_authorizations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_username", sa.String(length=64), nullable=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_telegram_binding_authorizations_telegram_user_id"),
        "telegram_binding_authorizations",
        ["telegram_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_telegram_binding_authorizations_telegram_chat_id"),
        "telegram_binding_authorizations",
        ["telegram_chat_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_telegram_binding_authorizations_token_hash"),
        "telegram_binding_authorizations",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_telegram_binding_authorizations_expires_at"),
        "telegram_binding_authorizations",
        ["expires_at"],
        unique=False,
    )

    op.create_table(
        "telegram_task_contexts",
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["reimbursement_tasks.id"]),
        sa.PrimaryKeyConstraint("telegram_user_id"),
    )
    op.create_index(
        op.f("ix_telegram_task_contexts_task_id"),
        "telegram_task_contexts",
        ["task_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_telegram_task_contexts_task_id"), table_name="telegram_task_contexts")
    op.drop_table("telegram_task_contexts")
    op.drop_index(
        op.f("ix_telegram_binding_authorizations_expires_at"),
        table_name="telegram_binding_authorizations",
    )
    op.drop_index(
        op.f("ix_telegram_binding_authorizations_token_hash"),
        table_name="telegram_binding_authorizations",
    )
    op.drop_index(
        op.f("ix_telegram_binding_authorizations_telegram_chat_id"),
        table_name="telegram_binding_authorizations",
    )
    op.drop_index(
        op.f("ix_telegram_binding_authorizations_telegram_user_id"),
        table_name="telegram_binding_authorizations",
    )
    op.drop_table("telegram_binding_authorizations")
