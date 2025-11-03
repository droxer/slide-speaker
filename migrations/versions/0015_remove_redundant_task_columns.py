"""remove redundant columns from task table that duplicate uploads table data

Revision ID: 0015_remove_redundant_cols
Revises: 0014_rename_file_id_to_upload_id
Create Date: 2025-10-12 21:30:00

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0015_remove_redundant_cols"
down_revision = "0014_rename_file_id_to_upload_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove redundant columns from tasks table that duplicate data in uploads table
    op.drop_column("tasks", "user_id")
    op.drop_column("tasks", "filename")
    op.drop_column("tasks", "file_ext")
    op.drop_column("tasks", "source_type")


def downgrade() -> None:
    # Add back the redundant columns
    op.add_column("tasks", sa.Column("user_id", sa.String(64), nullable=True))
    op.add_column("tasks", sa.Column("filename", sa.String(255), nullable=True))
    op.add_column("tasks", sa.Column("file_ext", sa.String(16), nullable=True))
    op.add_column("tasks", sa.Column("source_type", sa.String(32), nullable=True))

    # Recreate indexes if they existed
    op.create_index("ix_tasks_user_id", "tasks", ["user_id"], unique=False)
