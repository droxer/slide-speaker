"""add owner id to tasks

Revision ID: 0009_task_owner
Revises: 0008_pref_lang_users
Create Date: 2025-10-03 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0009_task_owner"
down_revision = "0008_pref_lang_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("owner_id", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_tasks_owner_id", "tasks", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tasks_owner_id", table_name="tasks")
    op.drop_column("tasks", "owner_id")
