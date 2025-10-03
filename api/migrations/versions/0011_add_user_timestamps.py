"""ensure users table tracks timestamps

Revision ID: 0011_add_user_timestamps
Revises: 0010_rename_task_id_to_id
Create Date: 2025-10-04 00:00:00
"""

from __future__ import annotations

from alembic import op

revision = "0011_add_user_timestamps"
down_revision = "0010_rename_task_id_to_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        """
    )
    op.execute(
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        """
    )
    op.execute("UPDATE users SET created_at = NOW() WHERE created_at IS NULL")
    op.execute("UPDATE users SET updated_at = NOW() WHERE updated_at IS NULL")
    op.execute("ALTER TABLE users ALTER COLUMN created_at SET DEFAULT NOW()")
    op.execute("ALTER TABLE users ALTER COLUMN updated_at SET DEFAULT NOW()")
    op.execute(
        "ALTER TABLE users ALTER COLUMN created_at SET NOT NULL, ALTER COLUMN updated_at SET NOT NULL"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS updated_at")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS created_at")
