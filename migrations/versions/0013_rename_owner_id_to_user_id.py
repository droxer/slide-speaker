"""rename owner_id to user_id in tasks and uploads tables

Revision ID: 0013_rename_owner_id_to_user_id
Revises: 0012_create_uploads_table
Create Date: 2025-10-12 19:27:37

"""

from __future__ import annotations

from alembic import op

revision = "0013_rename_owner_id_to_user_id"
down_revision = "0012_create_uploads_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename owner_id column to user_id in tasks table
    op.alter_column("tasks", "owner_id", new_column_name="user_id")

    # Rename index for tasks table if it exists
    # Drop the old index first
    op.drop_index("ix_tasks_owner_id", table_name="tasks", if_exists=True)
    # Create new index for user_id
    op.create_index("ix_tasks_user_id", "tasks", ["user_id"], unique=False)

    # Rename owner_id column to user_id in uploads table
    op.alter_column("uploads", "owner_id", new_column_name="user_id")

    # Rename index for uploads table if it exists
    # Drop the old index first
    op.drop_index("idx_uploads_owner_id", table_name="uploads", if_exists=True)
    # Create new index for user_id
    op.create_index("idx_uploads_user_id", "uploads", ["user_id"], unique=False)


def downgrade() -> None:
    # Rename user_id column back to owner_id in tasks table
    op.alter_column("tasks", "user_id", new_column_name="owner_id")

    # Rename index for tasks table back
    # Drop the new index first
    op.drop_index("ix_tasks_user_id", table_name="tasks", if_exists=True)
    # Create old index for owner_id
    op.create_index("ix_tasks_owner_id", "tasks", ["owner_id"], unique=False)

    # Rename user_id column back to owner_id in uploads table
    op.alter_column("uploads", "user_id", new_column_name="owner_id")

    # Rename index for uploads table back
    # Drop the new index first
    op.drop_index("idx_uploads_user_id", table_name="uploads", if_exists=True)
    # Create old index for owner_id
    op.create_index("idx_uploads_owner_id", "uploads", ["owner_id"], unique=False)
