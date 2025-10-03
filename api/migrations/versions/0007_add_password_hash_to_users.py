"""add password hash column to users

Revision ID: 0007_add_password_hash_to_users
Revises: 0006_add_file_metadata_columns
Create Date: 2024-09-21 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0007_add_password_hash_to_users"
down_revision = "0006_add_file_metadata_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "password_hash")
