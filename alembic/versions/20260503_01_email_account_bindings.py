"""add email account bindings and verification records

Revision ID: 20260503_01
Revises: 20260502_01
Create Date: 2026-05-03 17:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260503_01"
down_revision = "20260502_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_account_bindings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("member_id", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_email_account_bindings_member_id"),
        "email_account_bindings",
        ["member_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_email_account_bindings_email"),
        "email_account_bindings",
        ["email"],
        unique=True,
    )

    op.create_table(
        "email_binding_verifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("member_id", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_email_binding_verifications_member_id"),
        "email_binding_verifications",
        ["member_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_email_binding_verifications_email"),
        "email_binding_verifications",
        ["email"],
        unique=False,
    )
    op.create_index(
        "ix_email_binding_verification_member_email",
        "email_binding_verifications",
        ["member_id", "email", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_email_binding_verification_member_email", table_name="email_binding_verifications")
    op.drop_index(op.f("ix_email_binding_verifications_email"), table_name="email_binding_verifications")
    op.drop_index(op.f("ix_email_binding_verifications_member_id"), table_name="email_binding_verifications")
    op.drop_table("email_binding_verifications")

    op.drop_index(op.f("ix_email_account_bindings_email"), table_name="email_account_bindings")
    op.drop_index(op.f("ix_email_account_bindings_member_id"), table_name="email_account_bindings")
    op.drop_table("email_account_bindings")
