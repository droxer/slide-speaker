"""add preferred language to users

Revision ID: 0008_pref_lang_users
Revises: 0007_add_password_hash_to_users
Create Date: 2024-09-21 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0008_pref_lang_users"
down_revision = "0007_add_password_hash_to_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("preferred_language", sa.String(length=64), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE users SET preferred_language = 'english' WHERE preferred_language IS NULL"
        )
    )
    op.alter_column("users", "preferred_language", nullable=False)


def downgrade() -> None:
    op.drop_column("users", "preferred_language")
