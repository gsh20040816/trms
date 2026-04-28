"""add audit log skeleton

Revision ID: 20260428_03
Revises: 20260428_02
Create Date: 2026-04-28 18:05:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260428_03"
down_revision = "20260428_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("object_type", sa.String(length=64), nullable=False),
        sa.Column("object_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.String(length=1024), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["reimbursement_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_log_actor_created_at",
        "audit_logs",
        ["actor_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_log_object_created_at",
        "audit_logs",
        ["object_type", "object_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_log_request_id",
        "audit_logs",
        ["request_id"],
        unique=False,
    )
    op.create_index(
        "ix_audit_log_task_created_at",
        "audit_logs",
        ["task_id", "created_at"],
        unique=False,
    )
    op.create_index(op.f("ix_audit_logs_actor_id"), "audit_logs", ["actor_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_result"), "audit_logs", ["result"], unique=False)
    op.create_index(op.f("ix_audit_logs_task_id"), "audit_logs", ["task_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_task_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_result"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_actor_id"), table_name="audit_logs")
    op.drop_index("ix_audit_log_task_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_log_request_id", table_name="audit_logs")
    op.drop_index("ix_audit_log_object_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_log_actor_created_at", table_name="audit_logs")
    op.drop_table("audit_logs")
