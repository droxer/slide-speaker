"""rename file_id to upload_id in task table

Revision ID: 0014_rename_file_id_to_upload_id
Revises: 0013_rename_owner_id_to_user_id
Create Date: 2025-10-12 20:25:00

"""

from __future__ import annotations

from alembic import op

revision = "0014_rename_file_id_to_upload_id"
down_revision = "0013_rename_owner_id_to_user_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename file_id column to upload_id in tasks table
    op.alter_column("tasks", "file_id", new_column_name="upload_id")

    # Rename index for tasks table if it exists
    # Drop the old index first
    op.drop_index("idx_tasks_file_id", table_name="tasks", if_exists=True)
    # Create new index for upload_id - using the same name pattern as before
    op.create_index("idx_tasks_upload_id", "tasks", ["upload_id"], unique=False)

    # Update the foreign key constraint name
    # Drop and recreate the foreign key constraint to point to the renamed column
    op.drop_constraint("fk_tasks_file_id_uploads", "tasks", type_="foreignkey")
    op.create_foreign_key(
        "fk_tasks_upload_id_uploads",
        "tasks",
        "uploads",
        ["upload_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    # Rename upload_id column back to file_id in tasks table
    op.alter_column("tasks", "upload_id", new_column_name="file_id")

    # Rename index for tasks table back
    # Drop the new index first
    op.drop_index("idx_tasks_upload_id", table_name="tasks", if_exists=True)
    # Create old index for file_id
    op.create_index("idx_tasks_file_id", "tasks", ["file_id"], unique=False)

    # Restore the foreign key constraint name
    op.drop_constraint("fk_tasks_upload_id_uploads", "tasks", type_="foreignkey")
    op.create_foreign_key(
        "fk_tasks_file_id_uploads",
        "tasks",
        "uploads",
        ["file_id"],
        ["id"],
        ondelete="RESTRICT",
    )
