"""
Add filename and file_ext columns to tasks table.

Revision ID: 0006_add_file_metadata_columns
Revises: 0005_create_users_table
Create Date: 2025-09-24
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0006_add_file_metadata_columns"
down_revision = "0005_create_users_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(sa.Column("filename", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("file_ext", sa.String(length=16), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_column("file_ext")
        batch_op.drop_column("filename")
