"""
Task monitoring routes for comprehensive task tracking and management.

This module provides API endpoints for monitoring all presentation processing tasks,
including listing tasks, filtering, searching, and retrieving task statistics.
"""

from contextlib import suppress
from typing import Any

from fastapi import APIRouter, Query

from slidespeaker.core.progress_utils import compute_step_percentage
from slidespeaker.core.state_manager import state_manager
from slidespeaker.core.task_queue import task_queue
from slidespeaker.repository.task import (
    delete_task as db_delete_task,
)
from slidespeaker.repository.task import (
    list_tasks as db_list_tasks,
)

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/tasks")
async def get_tasks(
    status: str | None = Query(None, description="Filter by task status"),
    limit: int = Query(
        50, ge=1, le=1000, description="Maximum number of tasks to return"
    ),
    offset: int = Query(0, ge=0, description="Number of tasks to skip"),
    sort_by: str = Query(
        "created_at", description="Sort field (created_at, updated_at, status)"
    ),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
) -> dict[str, Any]:
    """DB-backed task list. Uses repository; no Redis scanning."""

    db_res = await db_list_tasks(limit=limit, offset=offset, status=status)
    return {
        "tasks": db_res["tasks"],
        "total": db_res["total"],
        "limit": limit,
        "offset": offset,
        "has_more": (db_res["total"] > offset + limit),
    }


@router.get("/tasks/db/{task_id}")
async def get_task_db(task_id: str) -> dict[str, Any]:
    """DB-only task fetch (no Redis/queue)."""
    from slidespeaker.repository.task import get_task as db_get_task

    row = await db_get_task(task_id)
    if not row:
        return {"error": "not_found", "task_id": task_id}
    return row


@router.delete("/tasks/db/{task_id}")
async def delete_task_db(task_id: str) -> dict[str, Any]:
    """DB-only delete for a task row (does not touch Redis/queue/state)."""
    try:
        await db_delete_task(task_id)
        return {"deleted": True, "task_id": task_id}
    except Exception as e:
        return {"deleted": False, "task_id": task_id, "error": str(e)}


@router.post("/admin/tasks/{task_id}/set_type")
async def set_task_type(
    task_id: str,
    task_type: str | None = None,
    generate_video: bool | None = None,
    generate_podcast: bool | None = None,
) -> dict[str, Any]:
    """Admin: update task type flags in state for a given task.

    Useful to correct legacy tasks where defaults caused mislabeling.
    """
    st = await state_manager.get_state_by_task(task_id)
    if not st:
        return {"updated": False, "error": "state_not_found"}
    if task_type is not None:
        st["task_type"] = task_type
    if generate_video is not None:
        st["generate_video"] = generate_video
    if generate_podcast is not None:
        st["generate_podcast"] = generate_podcast
    # Persist under task alias and file-id mirror
    st["task_id"] = task_id
    await state_manager.redis_client.set(
        f"ss:state:task:{task_id}", __import__("json").dumps(st), ex=86400
    )
    fid = st.get("file_id")
    if isinstance(fid, str) and fid:
        await state_manager.save_state(fid, st)
    return {"updated": True, "task_id": task_id, "state": st}


@router.get("/tasks/search")
async def search_tasks(
    query: str = Query(
        ...,
        description="Search query for task_id, file_id, status, task_type, or kwargs",
    ),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
) -> dict[str, Any]:
    """DB-backed search across basic fields. No Redis usage."""

    all_tasks_result = await db_list_tasks(limit=10000, offset=0, status=None)
    all_tasks = all_tasks_result["tasks"]

    q = query.lower()
    matches: list[dict[str, Any]] = []
    for t in all_tasks:
        if q in (t.get("task_id") or "").lower():
            matches.append(t)
            continue
        if q in (t.get("file_id") or "").lower():
            matches.append(t)
            continue
        if q in (t.get("status") or "").lower():
            matches.append(t)
            continue
        if q in (t.get("task_type") or "").lower():
            matches.append(t)
            continue
        kwargs = t.get("kwargs") or {}
        if kwargs and q in str(kwargs).lower():
            matches.append(t)

    matches = matches[:limit]
    return {"tasks": matches, "query": query, "total_found": len(matches)}


@router.get("/tasks/statistics")
async def get_task_statistics() -> dict[str, Any]:
    """Get comprehensive statistics about all tasks (DB only)."""
    from slidespeaker.repository.task import get_statistics as db_get_statistics

    return await db_get_statistics()


@router.get("/tasks/{task_id}")
async def get_task_details(task_id: str) -> dict[str, Any]:
    """Get detailed information about a specific task."""

    # Try to get from task queue first
    task = await task_queue.get_task(task_id)

    if not task and task_id.startswith("state_"):
        # Check if it's a state-only task (format: state_{file_id})
        file_id = task_id.replace("state_", "")
        state = await state_manager.get_state(file_id)
        if state:
            task = {
                "task_id": task_id,
                "file_id": file_id,
                "task_type": "process_presentation",
                "status": state["status"],
                "created_at": state["created_at"],
                "updated_at": state["updated_at"],
                "kwargs": {
                    "file_id": file_id,
                    "file_ext": state["file_ext"],
                    "source_type": state.get("source_type") or state.get("source"),
                    "voice_language": state["voice_language"],
                    "subtitle_language": state.get("subtitle_language"),
                    "generate_avatar": state["generate_avatar"],
                    "generate_subtitles": state["generate_subtitles"],
                },
                "state": state,
            }

    if not task:
        # DB fallback: reconstruct from DB + state
        from slidespeaker.repository.task import get_task as db_get_task

        row = await db_get_task(task_id)
        if row:
            file_id = str(row.get("file_id")) if row.get("file_id") is not None else ""
            st = await state_manager.get_state(file_id) if file_id else None
            return {
                "task_id": row.get("task_id"),
                "file_id": file_id,
                "task_type": row.get("task_type"),
                "status": row.get("status"),
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
                "kwargs": row.get("kwargs") or {},
                "source_type": (st or {}).get("source_type")
                or (st or {}).get("source")
                or (row.get("kwargs") or {}).get("source_type"),
                "state": st,
                "completion_percentage": compute_step_percentage(st) if st else 0,
            }
        return {"error": "Task not found", "task_id": task_id}

    # Enrich with detailed state information
    file_id = task.get("kwargs", {}).get("file_id", "unknown")
    if file_id != "unknown":
        state = await state_manager.get_state(file_id)
        if state:
            task["detailed_state"] = state

            # Add step completion percentage
            task["completion_percentage"] = compute_step_percentage(state)
            # Surface source_type at top level for convenience
            task["source_type"] = state.get("source_type") or state.get("source")

    return task


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str) -> dict[str, Any]:
    """Cancel a specific task if it's still running."""

    # Get task details
    task = await task_queue.get_task(task_id)

    if not task:
        return {
            "error": "Task not found",
            "task_id": task_id,
        }

    # Check if task can be cancelled
    if task["status"] not in ["queued", "processing"]:
        return {
            "error": f"Task cannot be cancelled in status: {task['status']}",
            "task_id": task_id,
            "current_status": task["status"],
        }

    # Cancel the task
    await task_queue.update_task_status(task_id, "cancelled")

    # Update state via task-id first (and file-id fallback)
    file_id = task.get("kwargs", {}).get("file_id")
    try:
        await state_manager.mark_cancelled_by_task(task_id)
    except Exception:
        if file_id:
            await state_manager.mark_cancelled(file_id)

    return {
        "message": "Task cancelled successfully",
        "task_id": task_id,
        "file_id": file_id,
    }


async def _resolve_file_id(task_id: str) -> str | None:
    """Resolve file_id via DB first, then queue/state"""
    file_id: str | None = None
    from slidespeaker.repository.task import get_task as db_get_task

    row = await db_get_task(task_id)
    if row:
        fid = row.get("file_id")
        file_id = str(fid) if fid is not None else None
    if not file_id:
        task = await task_queue.get_task(task_id)
        file_id = task.get("kwargs", {}).get("file_id") if task else None

    return file_id


async def _remove_from_queue(task_id: str, removed: dict[str, int]) -> None:
    """Remove task from queue (all occurrences)"""
    try:
        removed_count = await task_queue.redis_client.lrem(
            task_queue.queue_key,
            0,
            task_id,  # type: ignore
        )
        removed["queue"] = int(removed_count) if removed_count is not None else 0
    except Exception:
        pass


async def _delete_task_keys(
    task_key: str, cancellation_key: str, removed: dict[str, int]
) -> None:
    """Delete task key and cancellation flag"""
    # Delete task key
    try:
        del_count = await task_queue.redis_client.delete(task_key)
        removed["task"] = int(del_count) if del_count is not None else 0
    except Exception:
        pass

    # Delete cancellation flag
    try:
        del_count = await task_queue.redis_client.delete(cancellation_key)
        removed["cancel_flag"] = int(del_count) if del_count is not None else 0
    except Exception:
        pass


async def _handle_state_cleanup(
    file_id: str | None,
    task_id: str,
    state_key: str | None,
    task_state_key: str,
    file2task_key: str | None,
    file2tasks_set_key: str | None,
    removed: dict[str, int],
) -> int:
    """Handle state cleanup and return remaining task count"""
    # Remove task from file's multi-task set and decide whether to delete file state
    remaining = 0
    if file_id:
        try:
            remaining = await state_manager.unbind_task(file_id, task_id)
        except Exception:
            remaining = 0

    # Delete state key(s) only when no other tasks remain for this file
    if state_key and remaining == 0:
        try:
            del_count = await state_manager.redis_client.delete(state_key)
            removed["state"] = int(del_count) if del_count is not None else 0
        except Exception:
            pass

    try:
        del_count = await state_manager.redis_client.delete(task_state_key)
        removed["task_state"] = int(del_count) if del_count is not None else 0
    except Exception:
        pass

    return remaining


async def _delete_task_file_mappings(
    task2file_key: str,
    file2task_key: str | None,
    file2tasks_set_key: str | None,
    remaining: int,
    removed: dict[str, int],
) -> None:
    """Delete task↔file mappings"""
    # Delete task↔file mappings
    try:
        del_count = await task_queue.redis_client.delete(task2file_key)
        removed["task2file"] = int(del_count) if del_count is not None else 0
    except Exception:
        pass

    if file2task_key and remaining == 0:
        try:
            del_count = await task_queue.redis_client.delete(file2task_key)
            removed["file2task"] = int(del_count) if del_count is not None else 0
        except Exception:
            pass

    # If set is empty, also delete the set key
    if file2tasks_set_key and remaining == 0:
        with suppress(Exception):
            await state_manager.redis_client.delete(file2tasks_set_key)


@router.delete("/tasks/{task_id}/purge")
async def purge_task(task_id: str) -> dict[str, Any]:
    """Permanently delete a task and its state from the system.

    This removes the task entry, queue references, cancellation flags, and associated state.
    """
    try:
        # Resolve file_id via DB first, then queue/state
        file_id = await _resolve_file_id(task_id)

        # Build keys
        task_key = f"{task_queue.task_prefix}:{task_id}"
        cancellation_key = f"{task_queue.task_prefix}:{task_id}:cancelled"
        state_key = f"ss:state:{file_id}" if file_id else None
        task_state_key = f"ss:state:task:{task_id}"
        task2file_key = f"ss:task2file:{task_id}"
        file2task_key = f"ss:file2task:{file_id}" if file_id else None
        file2tasks_set_key = f"ss:file2tasks:{file_id}" if file_id else None

        removed = {
            "queue": 0,
            "task": 0,
            "cancel_flag": 0,
            "state": 0,
        }

        # Remove from queue (all occurrences)
        await _remove_from_queue(task_id, removed)

        # Delete task key and cancellation flag
        await _delete_task_keys(task_key, cancellation_key, removed)

        # Handle state cleanup
        remaining = await _handle_state_cleanup(
            file_id,
            task_id,
            state_key,
            task_state_key,
            file2task_key,
            file2tasks_set_key,
            removed,
        )

        # Delete task↔file mappings
        await _delete_task_file_mappings(
            task2file_key, file2task_key, file2tasks_set_key, remaining, removed
        )

        # Also remove from DB
        with suppress(Exception):
            await db_delete_task(task_id)

        return {
            "message": "Task purged successfully",
            "task_id": task_id,
            "file_id": file_id,
            "removed": removed,
        }
    except Exception as e:
        return {
            "error": f"Failed to purge task: {e}",
            "task_id": task_id,
            "file_id": file_id,
        }
