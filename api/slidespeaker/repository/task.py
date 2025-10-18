"""
Task repository backed by Postgres.

Persists tasks and status changes via SQLAlchemy. This module assumes the
database is configured and available.
"""

from __future__ import annotations

import hashlib
import json
from contextlib import suppress
from datetime import datetime
from typing import Any

from slidespeaker.configs.db import get_session
from slidespeaker.core.models import TaskRow, UploadRow
from slidespeaker.storage.paths import build_storage_uri

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
    return f"cache:{prefix}:{hashlib.md5(key_data.encode()).hexdigest()}"


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


async def _invalidate_cache(prefix: str) -> None:
    """Invalidate cached entries for a given prefix."""
    if not _cache_enabled or _redis_client is None:
        return
    pattern = f"cache:{prefix}:*"
    try:
        async for key in _redis_client.scan_iter(match=pattern, count=50):
            if key:
                await _redis_client.delete(key)
    except Exception:
        pass


def _filter_sensitive_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Filter out sensitive information from kwargs before returning in API responses."""
    filtered = kwargs.copy()
    # Remove sensitive fields that shouldn't be exposed to clients
    filtered.pop("file_path", None)
    filtered.pop("storage_object_key", None)
    return filtered


def _serialize_task(row: TaskRow) -> dict[str, Any]:
    """Serialize a TaskRow (and optional upload) into a response dict."""
    upload = getattr(row, "upload", None)
    kwargs = _filter_sensitive_kwargs(row.kwargs or {})
    upload_filename = upload.filename if upload and upload.filename else None
    upload_file_ext = upload.file_ext if upload and upload.file_ext else None
    filename = upload_filename or kwargs.get("filename")
    file_ext = upload_file_ext or kwargs.get("file_ext")

    data: dict[str, Any] = {
        "id": row.id,
        "task_id": row.id,
        "upload_id": row.upload_id,  # Internal model and API response now use upload_id for consistency
        "task_type": row.task_type,
        "status": row.status,
        "kwargs": kwargs,
        "error": row.error,
        "user_id": upload.user_id if upload else None,
        "voice_language": row.voice_language,
        "subtitle_language": row.subtitle_language,
        "source_type": upload.source_type if upload else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "filename": filename,
        "file_ext": file_ext,
    }
    if upload:
        data["upload"] = {
            "id": upload.id,
            "user_id": upload.user_id,
            "filename": upload.filename,
            "file_ext": upload.file_ext,
            "source_type": upload.source_type,
            "content_type": upload.content_type,
            "checksum": upload.checksum,
            "size_bytes": upload.size_bytes,
            "storage_path": upload.storage_path,
            "created_at": upload.created_at.isoformat() if upload.created_at else None,
            "updated_at": upload.updated_at.isoformat() if upload.updated_at else None,
        }
    return data


async def insert_task(task: dict[str, Any]) -> None:
    async with get_session() as s:
        now = datetime.now()

        # Extract and validate datetime values
        created_at_value = task.get("created_at")
        updated_at_value = task.get("updated_at")

        created_at = (
            datetime.fromisoformat(created_at_value)
            if created_at_value is not None and isinstance(created_at_value, str)
            else now
        )

        updated_at = (
            datetime.fromisoformat(updated_at_value)
            if updated_at_value is not None and isinstance(updated_at_value, str)
            else now
        )

        # Derive source_type from kwargs if present
        k = task.get("kwargs") or {}
        file_ext_raw = k.get("file_ext")
        file_ext = (file_ext_raw or "").lower()
        source_type = (
            "pdf"
            if file_ext == ".pdf"
            else ("slides" if file_ext in (".ppt", ".pptx") else None)
        )

        raw_file_id = (
            k.get("file_id")
            or task.get("file_id")
            or task.get("id")
            or task.get("task_id")
        )
        file_id = str(raw_file_id).strip() if raw_file_id else "unknown"
        if not file_id:
            file_id = "unknown"

        filename = k.get("filename")
        content_type = k.get("content_type")
        checksum = k.get("checksum")
        raw_size_bytes = k.get("file_size") or k.get("size_bytes")
        try:
            size_bytes = int(raw_size_bytes) if raw_size_bytes is not None else None
        except (TypeError, ValueError):
            size_bytes = None
        storage_object_key = k.get("storage_object_key") or k.get("storage_path")
        storage_uri = k.get("storage_uri")
        if not storage_uri and storage_object_key:
            storage_uri = build_storage_uri(str(storage_object_key))

        upload_row = await s.get(UploadRow, file_id)
        if upload_row is None:
            s.add(
                UploadRow(
                    id=file_id,
                    user_id=task.get("user_id"),
                    filename=filename or file_id,
                    file_ext=file_ext_raw,
                    source_type=source_type,
                    content_type=content_type,
                    checksum=checksum,
                    size_bytes=size_bytes,
                    storage_path=storage_uri,
                    created_at=created_at,
                    updated_at=updated_at,
                )
            )
        else:
            updated_upload = False
            user_id = task.get("user_id")
            if user_id and user_id != upload_row.user_id:
                upload_row.user_id = user_id
                updated_upload = True
            if filename and filename != upload_row.filename:
                upload_row.filename = filename
                updated_upload = True
            if file_ext_raw and file_ext_raw != upload_row.file_ext:
                upload_row.file_ext = file_ext_raw
                updated_upload = True
            if source_type and source_type != upload_row.source_type:
                upload_row.source_type = source_type
                updated_upload = True
            if content_type and content_type != upload_row.content_type:
                upload_row.content_type = content_type
                updated_upload = True
            if checksum and checksum != upload_row.checksum:
                upload_row.checksum = checksum
                updated_upload = True
            if size_bytes and size_bytes != upload_row.size_bytes:
                upload_row.size_bytes = size_bytes
                updated_upload = True
            if storage_uri and storage_uri != upload_row.storage_path:
                upload_row.storage_path = storage_uri
                updated_upload = True
            if updated_upload:
                upload_row.updated_at = updated_at

        # Decide which language to persist into subtitle_language column:
        # For podcast tasks, persist the transcript language selection under subtitle_language
        # so UI/analytics can surface it consistently. Fallback to provided subtitle_language
        # (or voice_language) when transcript_language is absent.
        task_type = (
            task.get("task_type", "process_presentation") or "process_presentation"
        )
        sub_lang: str | None
        if str(task_type).lower() == "podcast":
            sub_lang = (
                k.get("transcript_language")
                or k.get("subtitle_language")
                or k.get("voice_language")
            )
        else:
            sub_lang = k.get("subtitle_language")

        row = TaskRow(
            id=task.get("id") or task.get("task_id"),
            upload_id=file_id,
            task_type=task_type,
            status=task.get("status", "queued"),
            kwargs=task.get("kwargs"),
            error=task.get("error"),
            voice_language=k.get("voice_language"),
            subtitle_language=sub_lang,
            created_at=created_at,
            updated_at=updated_at,
        )
        s.add(row)
        await s.commit()
    await _invalidate_cache("list_tasks")


async def get_task(task_id: str) -> dict[str, Any] | None:
    """Fetch a single task row by task_id.

    Returns a plain dict or None when not found.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    async with get_session() as s:
        stmt = (
            select(TaskRow)
            .options(joinedload(TaskRow.upload))
            .where(TaskRow.id == task_id)
        )
        row = (await s.execute(stmt)).scalar_one_or_none()
        if not row:
            return None
        return _serialize_task(row)


async def get_file_id_by_task(task_id: str) -> str | None:
    """Return file_id for a given task_id using DB, or None if unavailable."""
    t = await get_task(task_id)
    return (t or {}).get("file_id") if t else None


async def get_tasks_by_upload_id(upload_id: str) -> list[dict[str, Any]]:
    """Return all tasks associated with a given upload_id."""
    from sqlalchemy import select

    from slidespeaker.core.models import TaskRow

    async with get_session() as s:
        query = select(TaskRow).where(TaskRow.upload_id == upload_id)
        result = await s.execute(query)
        rows = result.scalars().all()
        return [_serialize_task(r) for r in rows]


async def update_task(task_id: str, **fields: Any) -> None:
    """Update task fields by task_id without selecting the row.

    Avoids ORM SELECTs that could reference legacy columns on mismatched schemas.
    """
    from sqlalchemy import update as sa_update

    allowed = {
        "status",
        "error",
        "task_type",
        "kwargs",
        "voice_language",
        "subtitle_language",
        "upload_id",
        "created_at",
        "updated_at",
    }
    vals: dict[str, Any] = {k: v for k, v in fields.items() if k in allowed}
    if "updated_at" not in vals:
        vals["updated_at"] = datetime.now()
    if not vals:
        return
    async with get_session() as s:
        await s.execute(sa_update(TaskRow).where(TaskRow.id == task_id).values(**vals))
        await s.commit()
    await _invalidate_cache("list_tasks")


async def delete_task(task_id: str) -> None:
    """Delete a task row from DB by task_id (no-op if not found)."""
    from loguru import logger
    from sqlalchemy import delete as sa_delete

    logger.info(f"Repository: Attempting to delete task {task_id} from database")
    async with get_session() as s:
        result = await s.execute(sa_delete(TaskRow).where(TaskRow.id == task_id))
        await s.commit()
        # Log the number of affected rows if available
        rowcount = getattr(result, "rowcount", "unknown")
        logger.info(f"Repository: Delete operation affected {rowcount} rows")
    await _invalidate_cache("list_tasks")


async def list_tasks(
    limit: int,
    offset: int,
    status: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    from sqlalchemy import func, select, text
    from sqlalchemy.orm import joinedload

    # Generate cache key for this query
    cache_key = _generate_cache_key(
        "list_tasks", limit=limit, offset=offset, status=status, user_id=user_id
    )

    # Try to get from cache first
    cached_result = await _get_from_cache(cache_key)
    if cached_result is not None:
        return cached_result

    async with get_session() as s:
        # Use more efficient query with proper indexing
        base_query = select(TaskRow)
        if status:
            base_query = base_query.where(TaskRow.status == status)
        if user_id:
            base_query = base_query.join(TaskRow.upload).where(
                UploadRow.user_id == user_id
            )

        # Use count(*) for better performance
        total_query = select(func.count(text("1"))).select_from(base_query.subquery())
        total = (await s.execute(total_query)).scalar_one()

        # Optimize the data query with proper ordering and limits
        data_query = (
            base_query.options(joinedload(TaskRow.upload))
            .order_by(TaskRow.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await s.execute(data_query)).scalars().all()
        tasks = [_serialize_task(r) for r in rows]
        result = {"tasks": tasks, "total": int(total or 0)}

        # Cache the result for 5 minutes
        await _set_in_cache(cache_key, result, ttl=300)
        return result


async def get_statistics(user_id: str | None = None) -> dict[str, Any]:
    """Compute aggregate statistics from the DB."""
    from sqlalchemy import func, select, text

    async with get_session() as s:
        base_query = select(TaskRow)
        if user_id:
            base_query = base_query.join(TaskRow.upload).where(
                UploadRow.user_id == user_id
            )

        # Total
        total = (
            await s.execute(select(func.count()).select_from(base_query.subquery()))
        ).scalar_one()

        # Status breakdown
        status_stmt = select(TaskRow.status, func.count())
        if user_id:
            status_stmt = status_stmt.join(TaskRow.upload).where(
                UploadRow.user_id == user_id
            )
        rows = (await s.execute(status_stmt.group_by(TaskRow.status))).all()
        status_breakdown = {str(st): int(cnt) for st, cnt in rows}

        # Recent activity by created_at
        stmt_24 = (
            select(func.count())
            .select_from(TaskRow)
            .where(
                TaskRow.created_at >= text("(CURRENT_TIMESTAMP - INTERVAL '24 hours')")
            )
        )
        stmt_7 = (
            select(func.count())
            .select_from(TaskRow)
            .where(
                TaskRow.created_at >= text("(CURRENT_TIMESTAMP - INTERVAL '7 days')")
            )
        )
        stmt_30 = (
            select(func.count())
            .select_from(TaskRow)
            .where(
                TaskRow.created_at >= text("(CURRENT_TIMESTAMP - INTERVAL '30 days')")
            )
        )
        if user_id:
            stmt_24 = stmt_24.join(TaskRow.upload).where(UploadRow.user_id == user_id)
            stmt_7 = stmt_7.join(TaskRow.upload).where(UploadRow.user_id == user_id)
            stmt_30 = stmt_30.join(TaskRow.upload).where(UploadRow.user_id == user_id)
        last_24h = int((await s.execute(stmt_24)).scalar_one() or 0)
        last_7d = int((await s.execute(stmt_7)).scalar_one() or 0)
        last_30d = int((await s.execute(stmt_30)).scalar_one() or 0)

        # Language stats from stored columns (if populated)
        voice_stmt = select(TaskRow.voice_language, func.count()).where(
            TaskRow.voice_language.is_not(None)
        )
        subtitle_stmt = select(TaskRow.subtitle_language, func.count()).where(
            TaskRow.subtitle_language.is_not(None)
        )
        if user_id:
            voice_stmt = voice_stmt.join(TaskRow.upload).where(
                UploadRow.user_id == user_id
            )
            subtitle_stmt = subtitle_stmt.join(TaskRow.upload).where(
                UploadRow.user_id == user_id
            )
        voice_rows = (
            await s.execute(voice_stmt.group_by(TaskRow.voice_language))
        ).all()
        subtitle_rows = (
            await s.execute(subtitle_stmt.group_by(TaskRow.subtitle_language))
        ).all()
        language_stats: dict[str, int] = {}
        for lang, cnt in voice_rows:
            language_stats[str(lang)] = language_stats.get(str(lang), 0) + int(cnt or 0)
        for lang, cnt in subtitle_rows:
            # Avoid double counting if same lang tracked in both; still mirror UI logic
            language_stats[str(lang)] = language_stats.get(str(lang), 0) + int(cnt or 0)

        # Processing stats
        # Average processing time for completed = avg(updated_at - created_at) minutes
        avg_stmt = select(
            func.avg(func.extract("epoch", TaskRow.updated_at - TaskRow.created_at))
        ).where(TaskRow.status == "completed")
        if user_id:
            avg_stmt = avg_stmt.join(TaskRow.upload).where(UploadRow.user_id == user_id)
        avg_proc = (await s.execute(avg_stmt)).scalar()
        avg_minutes = round(float(avg_proc) / 60.0, 2) if avg_proc else None

        completed = status_breakdown.get("completed", 0)
        failed = status_breakdown.get("failed", 0)
        success_rate = (completed / total * 100.0) if total else 0.0
        failed_rate = (failed / total * 100.0) if total else 0.0

        return {
            "total_tasks": int(total or 0),
            "status_breakdown": status_breakdown,
            "language_stats": language_stats,
            "recent_activity": {
                "last_24h": int(last_24h or 0),
                "last_7d": int(last_7d or 0),
                "last_30d": int(last_30d or 0),
            },
            "processing_stats": {
                "avg_processing_time_minutes": avg_minutes,
                "success_rate": round(success_rate, 2),
                "failed_rate": round(failed_rate, 2),
            },
        }
