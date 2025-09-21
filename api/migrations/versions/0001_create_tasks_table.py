from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0001_create_tasks_table"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("task_id", sa.String(length=64), primary_key=True),
        sa.Column("file_id", sa.String(length=64), nullable=False),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "kwargs", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("generate_video", sa.Boolean(), nullable=True),
        sa.Column("generate_podcast", sa.Boolean(), nullable=True),
        sa.Column("voice_language", sa.String(length=64), nullable=True),
        sa.Column("subtitle_language", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_tasks_file_id", "tasks", ["file_id"], unique=False)
    op.create_index("idx_tasks_status", "tasks", ["status"], unique=False)
    op.create_index("idx_tasks_created_at", "tasks", ["created_at"], unique=False)
    op.create_index("idx_tasks_updated_at", "tasks", ["updated_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_tasks_updated_at", table_name="tasks")
    op.drop_index("idx_tasks_created_at", table_name="tasks")
    op.drop_index("idx_tasks_status", table_name="tasks")
    op.drop_index("idx_tasks_file_id", table_name="tasks")
    op.drop_table("tasks")
