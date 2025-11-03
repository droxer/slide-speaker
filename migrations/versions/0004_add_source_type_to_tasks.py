from __future__ import annotations

from contextlib import suppress

import sqlalchemy as sa

from alembic import op

revision = "0004_add_source_type_to_tasks"
down_revision = "0003_drop_generate_flags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add nullable source_type and backfill from kwargs->file_ext when available
    op.add_column(
        "tasks", sa.Column("source_type", sa.String(length=32), nullable=True)
    )
    # Best-effort backfill using file extension hints in kwargs
    with suppress(Exception):
        op.execute(
            """
            UPDATE tasks
            SET source_type = CASE
              WHEN (kwargs->>'file_ext') ILIKE '%.pdf' THEN 'pdf'
              WHEN (kwargs->>'file_ext') ILIKE '%.pptx' OR (kwargs->>'file_ext') ILIKE '%.ppt' THEN 'slides'
              ELSE NULL
            END
            WHERE source_type IS NULL
            """
        )


def downgrade() -> None:
    op.drop_column("tasks", "source_type")
