from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0002_add_autoincrement_id"
down_revision = "0001_create_tasks_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add auto-incrementing ID column
    op.add_column(
        "tasks", sa.Column("id", sa.Integer(), autoincrement=True, nullable=False)
    )

    # Create a sequence for the ID column
    op.execute("CREATE SEQUENCE tasks_id_seq")

    # Set the column to use the sequence as default
    op.execute("ALTER TABLE tasks ALTER COLUMN id SET DEFAULT nextval('tasks_id_seq')")

    # Set the sequence to be owned by the column
    op.execute("ALTER SEQUENCE tasks_id_seq OWNED BY tasks.id")

    # Create a unique index on the new ID column for faster lookups
    op.create_index("idx_tasks_id", "tasks", ["id"], unique=True)


def downgrade() -> None:
    # Drop the index
    op.drop_index("idx_tasks_id", table_name="tasks")

    # Remove the default value
    op.execute("ALTER TABLE tasks ALTER COLUMN id DROP DEFAULT")

    # Drop the sequence
    op.execute("DROP SEQUENCE tasks_id_seq")

    # Drop the column
    op.drop_column("tasks", "id")
