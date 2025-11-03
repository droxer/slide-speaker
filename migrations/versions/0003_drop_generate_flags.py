from __future__ import annotations

from contextlib import suppress

import sqlalchemy as sa

from alembic import op

revision = "0003_drop_generate_flags"
down_revision = "0002_add_autoincrement_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Backfill task_type from legacy flags where necessary
    op.execute(
        """
        UPDATE tasks
        SET task_type = CASE
            WHEN generate_video IS TRUE AND (generate_podcast IS NULL OR generate_podcast = FALSE) THEN 'video'
            WHEN generate_podcast IS TRUE AND (generate_video IS NULL OR generate_video = FALSE) THEN 'podcast'
            WHEN generate_video IS TRUE AND generate_podcast IS TRUE THEN 'both'
            ELSE task_type
        END
        WHERE task_type IS NULL OR task_type = 'process_presentation'
        """
    )

    # Drop legacy columns
    with op.batch_alter_table("tasks") as batch_op:
        with suppress(Exception):
            batch_op.drop_column("generate_video")
        with suppress(Exception):
            batch_op.drop_column("generate_podcast")


def downgrade() -> None:
    # Re-create legacy columns
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(sa.Column("generate_video", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("generate_podcast", sa.Boolean(), nullable=True))

    # Backfill flags from task_type
    op.execute(
        """
        UPDATE tasks
        SET generate_video = CASE WHEN task_type IN ('video','both') THEN TRUE ELSE FALSE END,
            generate_podcast = CASE WHEN task_type IN ('podcast','both') THEN TRUE ELSE FALSE END
        """
    )
