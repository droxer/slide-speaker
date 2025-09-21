"""
Task repository backed by Postgres.

Persists tasks and status changes via SQLAlchemy. This module assumes the
database is configured and available.
"""

from __future__ import annotations

from contextlib import suppress
from datetime import datetime
from typing import Any

from slidespeaker.configs.db import get_session
from slidespeaker.core.models import TaskRow


def _filter_sensitive_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Filter out sensitive information from kwargs before returning in API responses."""
    filtered = kwargs.copy()
    # Remove sensitive fields that shouldn't be exposed to clients
    filtered.pop("file_path", None)
    return filtered


async def create_tables() -> None:
    from sqlalchemy import text

    async with get_session() as s:
        # Create table
        await s.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                  task_id VARCHAR(64) PRIMARY KEY,
                  file_id VARCHAR(64) NOT NULL,
                  task_type VARCHAR(64) NOT NULL,
                  status VARCHAR(32) NOT NULL,
                  kwargs JSONB,
                  error TEXT,
                  generate_video BOOLEAN,
                  generate_podcast BOOLEAN,
                  voice_language VARCHAR(64),
                  subtitle_language VARCHAR(64),
                  created_at TIMESTAMP NOT NULL,
                  updated_at TIMESTAMP NOT NULL
                )
                """
            )
        )

        # Create indexes
        await s.execute(
            text("CREATE INDEX IF NOT EXISTS idx_tasks_file_id ON tasks(file_id)")
        )
        await s.execute(
            text("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        )
        await s.execute(
            text("CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)")
        )
        await s.execute(
            text("CREATE INDEX IF NOT EXISTS idx_tasks_updated_at ON tasks(updated_at)")
        )

        # Add columns if they don't exist (backfill)
        with suppress(Exception):
            await s.execute(
                text(
                    "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS voice_language VARCHAR(64)"
                )
            )

        with suppress(Exception):
            await s.execute(
                text(
                    "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS subtitle_language VARCHAR(64)"
                )
            )

        # generate_* columns deprecated; task_type is the source of truth

        await s.commit()


async def insert_task(task: dict[str, Any]) -> None:
    await create_tables()
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
        file_ext = (k.get("file_ext") or "").lower()
        source_type = (
            "pdf"
            if file_ext == ".pdf"
            else ("slides" if file_ext in (".ppt", ".pptx") else None)
        )

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
            task_id=task.get("task_id"),
            file_id=k.get("file_id", "unknown"),
            task_type=task_type,
            status=task.get("status", "queued"),
            kwargs=task.get("kwargs"),
            error=task.get("error"),
            voice_language=k.get("voice_language"),
            subtitle_language=sub_lang,
            source_type=source_type,
            created_at=created_at,
            updated_at=updated_at,
        )
        s.add(row)
        await s.commit()


async def get_task(task_id: str) -> dict[str, Any] | None:
    """Fetch a single task row by task_id.

    Returns a plain dict or None when not found.
    """
    await create_tables()
    from sqlalchemy import select

    async with get_session() as s:
        row = (
            await s.execute(select(TaskRow).where(TaskRow.task_id == task_id))
        ).scalar_one_or_none()
        if not row:
            return None
        return {
            "task_id": row.task_id,
            "file_id": row.file_id,
            "task_type": row.task_type,
            "status": row.status,
            "kwargs": _filter_sensitive_kwargs(row.kwargs or {}),
            "error": row.error,
            "voice_language": row.voice_language,
            "subtitle_language": row.subtitle_language,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }


async def get_file_id_by_task(task_id: str) -> str | None:
    """Return file_id for a given task_id using DB, or None if unavailable."""
    t = await get_task(task_id)
    return (t or {}).get("file_id") if t else None


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
        "file_id",
        "created_at",
        "updated_at",
    }
    vals: dict[str, Any] = {k: v for k, v in fields.items() if k in allowed}
    if "updated_at" not in vals:
        vals["updated_at"] = datetime.now()
    if not vals:
        return
    async with get_session() as s:
        await s.execute(
            sa_update(TaskRow).where(TaskRow.task_id == task_id).values(**vals)
        )
        await s.commit()


async def delete_task(task_id: str) -> None:
    """Delete a task row from DB by task_id (no-op if not found)."""
    from sqlalchemy import delete as sa_delete

    async with get_session() as s:
        await s.execute(sa_delete(TaskRow).where(TaskRow.task_id == task_id))
        await s.commit()


async def list_tasks(
    limit: int, offset: int, status: str | None = None
) -> dict[str, Any]:
    from sqlalchemy import func, select

    async with get_session() as s:
        q = select(TaskRow)
        if status:
            q = q.where(TaskRow.status == status)
        total = (
            await s.execute(select(func.count()).select_from(q.subquery()))
        ).scalar_one()
        rows = (
            (
                await s.execute(
                    q.order_by(TaskRow.created_at.desc()).limit(limit).offset(offset)
                )
            )
            .scalars()
            .all()
        )
        tasks = [
            {
                "task_id": r.task_id,
                "file_id": r.file_id,
                "task_type": r.task_type,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
                "kwargs": _filter_sensitive_kwargs(r.kwargs or {}),
                # Surface language hints for UI if needed in the future
                "voice_language": r.voice_language,
                "subtitle_language": r.subtitle_language,
                "source_type": r.source_type,
            }
            for r in rows
        ]
        return {"tasks": tasks, "total": int(total or 0)}


async def get_statistics() -> dict[str, Any]:
    """Compute aggregate statistics from the DB."""
    from sqlalchemy import func, select, text

    await create_tables()
    async with get_session() as s:
        # Total
        total = (
            await s.execute(select(func.count()).select_from(TaskRow))
        ).scalar_one()

        # Status breakdown
        rows = (
            await s.execute(
                select(TaskRow.status, func.count()).group_by(TaskRow.status)
            )
        ).all()
        status_breakdown = {str(st): int(cnt) for st, cnt in rows}

        # Recent activity by created_at
        last_24h = (
            await s.execute(
                select(func.count())
                .select_from(TaskRow)
                .where(
                    TaskRow.created_at
                    >= text("(CURRENT_TIMESTAMP - INTERVAL '24 hours')")
                )
            )
        ).scalar_one()
        last_7d = (
            await s.execute(
                select(func.count())
                .select_from(TaskRow)
                .where(
                    TaskRow.created_at
                    >= text("(CURRENT_TIMESTAMP - INTERVAL '7 days')")
                )
            )
        ).scalar_one()
        last_30d = (
            await s.execute(
                select(func.count())
                .select_from(TaskRow)
                .where(
                    TaskRow.created_at
                    >= text("(CURRENT_TIMESTAMP - INTERVAL '30 days')")
                )
            )
        ).scalar_one()

        # Language stats from stored columns (if populated)
        voice_rows = (
            await s.execute(
                select(TaskRow.voice_language, func.count())
                .where(TaskRow.voice_language.is_not(None))
                .group_by(TaskRow.voice_language)
            )
        ).all()
        subtitle_rows = (
            await s.execute(
                select(TaskRow.subtitle_language, func.count())
                .where(TaskRow.subtitle_language.is_not(None))
                .group_by(TaskRow.subtitle_language)
            )
        ).all()
        language_stats: dict[str, int] = {}
        for lang, cnt in voice_rows:
            language_stats[str(lang)] = language_stats.get(str(lang), 0) + int(cnt or 0)
        for lang, cnt in subtitle_rows:
            # Avoid double counting if same lang tracked in both; still mirror UI logic
            language_stats[str(lang)] = language_stats.get(str(lang), 0) + int(cnt or 0)

        # Processing stats
        # Average processing time for completed = avg(updated_at - created_at) minutes
        avg_proc = (
            await s.execute(
                select(
                    func.avg(
                        func.extract("epoch", TaskRow.updated_at - TaskRow.created_at)
                    )
                ).where(TaskRow.status == "completed")
            )
        ).scalar()
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
