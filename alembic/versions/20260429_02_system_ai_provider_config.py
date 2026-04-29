"""add system ai provider config

Revision ID: 20260429_02
Revises: 20260429_01
Create Date: 2026-04-29 13:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260429_02"
down_revision = "20260429_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_ai_provider_configs",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("text_llm_base_url", sa.String(length=255), nullable=True),
        sa.Column("text_llm_model", sa.String(length=255), nullable=True),
        sa.Column("text_llm_timeout_seconds", sa.Float(), nullable=True),
        sa.Column("text_llm_max_retries", sa.Integer(), nullable=True),
        sa.Column("text_llm_api_key", sa.String(length=512), nullable=True),
        sa.Column("vlm_base_url", sa.String(length=255), nullable=True),
        sa.Column("vlm_model", sa.String(length=255), nullable=True),
        sa.Column("vlm_timeout_seconds", sa.Float(), nullable=True),
        sa.Column("vlm_max_retries", sa.Integer(), nullable=True),
        sa.Column("vlm_api_key", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("system_ai_provider_configs")
