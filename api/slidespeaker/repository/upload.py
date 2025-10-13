"""
Upload repository for managing uploaded file metadata.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select

from slidespeaker.configs.db import get_session
from slidespeaker.core.models import UploadRow


async def upsert_upload(
    *,
    file_id: str,
    user_id: str | None = None,
    filename: str | None = None,
    file_ext: str | None = None,
    source_type: str | None = None,
    content_type: str | None = None,
    checksum: str | None = None,
    size_bytes: int | None = None,
    storage_path: str | None = None,
) -> None:
    """Insert or update an upload record."""
    now = datetime.now()
    async with get_session() as session:
        row = await session.get(UploadRow, file_id)
        if row is None:
            session.add(
                UploadRow(
                    id=file_id,
                    user_id=user_id,
                    filename=filename or file_id,
                    file_ext=file_ext,
                    source_type=source_type,
                    content_type=content_type,
                    checksum=checksum,
                    size_bytes=size_bytes,
                    storage_path=storage_path,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            updated = False
            if user_id and user_id != row.user_id:
                row.user_id = user_id
                updated = True
            if filename and filename != row.filename:
                row.filename = filename
                updated = True
            if file_ext and file_ext != row.file_ext:
                row.file_ext = file_ext
                updated = True
            if source_type and source_type != row.source_type:
                row.source_type = source_type
                updated = True
            if content_type and content_type != row.content_type:
                row.content_type = content_type
                updated = True
            if checksum and checksum != row.checksum:
                row.checksum = checksum
                updated = True
            if size_bytes and size_bytes != row.size_bytes:
                row.size_bytes = size_bytes
                updated = True
            if storage_path and storage_path != row.storage_path:
                row.storage_path = storage_path
                updated = True
            if updated:
                row.updated_at = now
        await session.commit()


async def get_upload(file_id: str) -> dict[str, Any] | None:
    """Fetch an upload row as a dict."""
    async with get_session() as session:
        row = await session.get(UploadRow, file_id)
        if row is None:
            return None
        return {
            "id": row.id,
            "user_id": row.user_id,
            "filename": row.filename,
            "file_ext": row.file_ext,
            "source_type": row.source_type,
            "content_type": row.content_type,
            "checksum": row.checksum,
            "size_bytes": row.size_bytes,
            "storage_path": row.storage_path,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }


async def list_uploads_for_user(user_id: str) -> list[dict[str, Any]]:
    """List uploads belonging to an owner."""
    async with get_session() as session:
        stmt = select(UploadRow).where(UploadRow.user_id == user_id)
        rows = (await session.execute(stmt)).scalars().all()
        return [
            {
                "id": row.id,
                "user_id": row.user_id,
                "filename": row.filename,
                "file_ext": row.file_ext,
                "source_type": row.source_type,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ]
