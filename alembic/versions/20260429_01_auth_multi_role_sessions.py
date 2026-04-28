"""add multi-role auth session support

Revision ID: 20260429_01
Revises: 20260428_03
Create Date: 2026-04-29 05:20:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260429_01"
down_revision = "20260428_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_accounts",
        sa.Column("roles", sa.JSON(), nullable=True),
    )
    op.add_column(
        "auth_sessions",
        sa.Column("active_role", sa.String(length=32), nullable=True),
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("UPDATE user_accounts SET roles = json_build_array(role) WHERE roles IS NULL")
    else:
        op.execute(
            """
            UPDATE user_accounts
            SET roles = '["' || role || '"]'
            WHERE roles IS NULL
            """
        )

    op.execute(
        """
        UPDATE auth_sessions
        SET active_role = (
            SELECT user_accounts.role
            FROM user_accounts
            WHERE user_accounts.id = auth_sessions.user_id
        )
        WHERE active_role IS NULL
        """
    )

    with op.batch_alter_table("user_accounts") as batch_op:
        batch_op.alter_column("roles", existing_type=sa.JSON(), nullable=False)

    with op.batch_alter_table("auth_sessions") as batch_op:
        batch_op.alter_column("active_role", existing_type=sa.String(length=32), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("auth_sessions") as batch_op:
        batch_op.drop_column("active_role")

    with op.batch_alter_table("user_accounts") as batch_op:
        batch_op.drop_column("roles")
