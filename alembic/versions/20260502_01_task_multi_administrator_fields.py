"""add task multi administrator fields

Revision ID: 20260502_01
Revises: 20260501_02
Create Date: 2026-05-02 13:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260502_01"
down_revision = "20260501_02"
branch_labels = None
depends_on = None


task_table = sa.table(
    "reimbursement_tasks",
    sa.column("id", sa.String(length=36)),
    sa.column("administrator_id", sa.String(length=128)),
    sa.column("administrator_ids", sa.JSON()),
)


def upgrade() -> None:
    op.add_column(
        "reimbursement_tasks",
        sa.Column("administrator_ids", sa.JSON(), nullable=True),
    )

    bind = op.get_bind()
    rows = bind.execute(
        sa.select(task_table.c.id, task_table.c.administrator_id)
    ).mappings()
    for row in rows:
        bind.execute(
            task_table.update()
            .where(task_table.c.id == row["id"])
            .values(administrator_ids=[row["administrator_id"]])
        )


def downgrade() -> None:
    op.drop_column("reimbursement_tasks", "administrator_ids")
