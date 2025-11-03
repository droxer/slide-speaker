"""rename task_id column to id on tasks

Revision ID: 0010_rename_task_id_to_id
Revises: 0009_task_owner
Create Date: 2025-10-03 00:30:00
"""

from __future__ import annotations

from alembic import op

revision = "0010_rename_task_id_to_id"
down_revision = "0009_task_owner"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE tasks DROP COLUMN IF EXISTS id")
    op.alter_column("tasks", "task_id", new_column_name="id")


def downgrade() -> None:
    op.alter_column("tasks", "id", new_column_name="task_id")
