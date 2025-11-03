"""add preferred_theme column to users

Revision ID: 0017_add_preferred_theme_column
Revises: 0016_add_indexes_for_performance
Create Date: 2025-10-19 13:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0017_add_preferred_theme_column"
down_revision = "0016_add_indexes_for_performance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add the preferred_theme column to the users table
    op.add_column("users", sa.Column("preferred_theme", sa.String(32), nullable=True))


def downgrade() -> None:
    # Remove the preferred_theme column from the users table
    op.drop_column("users", "preferred_theme")
