"""add registration policy and registration email verifications

Revision ID: 20260504_01
Revises: 20260503_04
Create Date: 2026-05-04 03:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260504_01"
down_revision = "20260503_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "registration_policies",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("allowed_email_hosts", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "registration_email_verifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_registration_email_verifications_email"),
        "registration_email_verifications",
        ["email"],
        unique=False,
    )
    op.create_index(
        "ix_registration_email_verification_email",
        "registration_email_verifications",
        ["email", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_registration_email_verification_email",
        table_name="registration_email_verifications",
    )
    op.drop_index(
        op.f("ix_registration_email_verifications_email"),
        table_name="registration_email_verifications",
    )
    op.drop_table("registration_email_verifications")
    op.drop_table("registration_policies")
