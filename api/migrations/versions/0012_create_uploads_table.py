"""
Create uploads table to store uploaded file metadata.

Revision ID: 0012_create_uploads_table
Revises: 0011_add_user_timestamps
Create Date: 2025-01-20
"""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0012_create_uploads_table"
down_revision = "0011_add_user_timestamps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "uploads",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.String(length=64), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("file_ext", sa.String(length=16), nullable=True),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_uploads_owner_id", "uploads", ["owner_id"], unique=False)

    conn = op.get_bind()
    uploads_table = sa.table(
        "uploads",
        sa.Column("id", sa.String(length=64)),
        sa.Column("owner_id", sa.String(length=64)),
        sa.Column("filename", sa.String(length=255)),
        sa.Column("file_ext", sa.String(length=16)),
        sa.Column("content_type", sa.String(length=128)),
        sa.Column("checksum", sa.String(length=128)),
        sa.Column("size_bytes", sa.BigInteger()),
        sa.Column("storage_path", sa.Text()),
        sa.Column("source_type", sa.String(length=32)),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )

    result = conn.execute(
        sa.text(
            """
            SELECT DISTINCT ON (file_id)
                file_id,
                COALESCE(filename, kwargs->>'filename') AS filename,
                COALESCE(file_ext, kwargs->>'file_ext') AS file_ext,
                owner_id,
                source_type,
                created_at,
                updated_at
            FROM tasks
            WHERE file_id IS NOT NULL AND file_id <> ''
            ORDER BY file_id, created_at
            """
        )
    )
    rows = result.mappings().all()
    if rows:
        now = datetime.utcnow()
        payload: list[dict[str, object]] = []
        for row in rows:
            file_id = row.get("file_id")
            if not file_id:
                continue
            filename = row.get("filename") or str(file_id)
            file_ext = row.get("file_ext")
            if isinstance(file_ext, str):
                file_ext = file_ext.strip() or None
            owner_id = row.get("owner_id")
            source_type = row.get("source_type")
            created_at = row.get("created_at") or now
            updated_at = row.get("updated_at") or created_at
            storage_path = None
            if file_ext:
                storage_path = f"uploads/{file_id}{file_ext}"
            payload.append(
                {
                    "id": str(file_id),
                    "owner_id": owner_id if owner_id else None,
                    "filename": filename,
                    "file_ext": file_ext,
                    "content_type": None,
                    "checksum": None,
                    "size_bytes": None,
                    "storage_path": storage_path,
                    "source_type": source_type,
                    "created_at": created_at,
                    "updated_at": updated_at,
                }
            )

        if payload:
            op.bulk_insert(uploads_table, payload)

    op.create_foreign_key(
        "fk_tasks_file_id_uploads",
        "tasks",
        "uploads",
        ["file_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_tasks_file_id_uploads", "tasks", type_="foreignkey")
    op.drop_index("idx_uploads_owner_id", table_name="uploads")
    op.drop_table("uploads")
