"""
Add indexes for performance optimization on frequently queried columns.

Revision ID: 0016_add_indexes_for_performance
Revises: 0015_remove_redundant_cols
Create Date: 2025-10-16 16:00:00
"""

from __future__ import annotations

from contextlib import suppress

from alembic import op

# revision identifiers, used by Alembic.
revision = "0016_add_indexes_for_performance"
down_revision = "0015_remove_redundant_cols"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add indexes for frequently queried columns in tasks table
    # Use contextlib.suppress to handle cases where indexes already exist
    with suppress(Exception):
        op.create_index("idx_tasks_status", "tasks", ["status"], unique=False)

    with suppress(Exception):
        op.create_index("idx_tasks_created_at", "tasks", ["created_at"], unique=False)

    with suppress(Exception):
        op.create_index("idx_tasks_updated_at", "tasks", ["updated_at"], unique=False)

    with suppress(Exception):
        op.create_index("idx_tasks_task_type", "tasks", ["task_type"], unique=False)

    # Add composite indexes for common query patterns
    with suppress(Exception):
        op.create_index(
            "idx_tasks_user_created", "tasks", ["upload_id", "created_at"], unique=False
        )

    with suppress(Exception):
        op.create_index(
            "idx_tasks_user_status", "tasks", ["upload_id", "status"], unique=False
        )

    with suppress(Exception):
        op.create_index(
            "idx_tasks_status_created", "tasks", ["status", "created_at"], unique=False
        )

    # Add indexes for uploads table
    with suppress(Exception):
        op.create_index(
            "idx_uploads_created_at", "uploads", ["created_at"], unique=False
        )

    with suppress(Exception):
        op.create_index(
            "idx_uploads_user_created",
            "uploads",
            ["user_id", "created_at"],
            unique=False,
        )

    with suppress(Exception):
        op.create_index(
            "idx_uploads_source_type", "uploads", ["source_type"], unique=False
        )


def downgrade() -> None:
    # Remove indexes
    with suppress(Exception):
        op.drop_index("idx_tasks_status", table_name="tasks")

    with suppress(Exception):
        op.drop_index("idx_tasks_created_at", table_name="tasks")

    with suppress(Exception):
        op.drop_index("idx_tasks_updated_at", table_name="tasks")

    with suppress(Exception):
        op.drop_index("idx_tasks_task_type", table_name="tasks")

    with suppress(Exception):
        op.drop_index("idx_tasks_user_created", table_name="tasks")

    with suppress(Exception):
        op.drop_index("idx_tasks_user_status", table_name="tasks")

    with suppress(Exception):
        op.drop_index("idx_tasks_status_created", table_name="tasks")

    with suppress(Exception):
        op.drop_index("idx_uploads_created_at", table_name="uploads")

    with suppress(Exception):
        op.drop_index("idx_uploads_user_created", table_name="uploads")

    with suppress(Exception):
        op.drop_index("idx_uploads_source_type", table_name="uploads")
