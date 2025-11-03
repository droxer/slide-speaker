"""
Upload repository for managing uploaded file metadata.
"""

from __future__ import annotations

import hashlib
import json
from contextlib import suppress
from datetime import datetime
from typing import Any

from sqlalchemy import select

from slidespeaker.configs.db import get_session
from slidespeaker.core.models import UploadRow

# Import Redis for caching
try:
    from slidespeaker.configs.redis_config import RedisConfig

    _redis_client = RedisConfig.get_redis_client()
    _cache_enabled = True
except Exception:
    _redis_client = None
    _cache_enabled = False


def _generate_cache_key(prefix: str, **kwargs: Any) -> str:
    """Generate a cache key from function arguments."""
    # Create a deterministic key based on arguments
    key_data = f"{prefix}:{json.dumps(kwargs, sort_keys=True)}"
    return f"cache:{hashlib.md5(key_data.encode()).hexdigest()}"


async def _get_from_cache(key: str) -> Any | None:
    """Get value from cache if enabled."""
    if not _cache_enabled or _redis_client is None:
        return None
    with suppress(Exception):
        cached = await _redis_client.get(key)
        if cached:
            return json.loads(cached)
    return None


async def _set_in_cache(key: str, value: Any, ttl: int = 300) -> None:
    """Set value in cache if enabled."""
    if not _cache_enabled or _redis_client is None:
        return
    with suppress(Exception):
        await _redis_client.setex(key, ttl, json.dumps(value))


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
    # Generate cache key for this query
    cache_key = _generate_cache_key("list_uploads_for_user", user_id=user_id)

    # Try to get from cache first
    cached_result = await _get_from_cache(cache_key)
    if cached_result is not None:
        return cached_result

    async with get_session() as session:
        stmt = select(UploadRow).where(UploadRow.user_id == user_id)
        rows = (await session.execute(stmt)).scalars().all()
        result = [
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

        # Cache the result for 5 minutes
        await _set_in_cache(cache_key, result, ttl=300)
        return result
