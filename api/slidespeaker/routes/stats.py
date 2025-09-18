"""
Task monitoring routes for comprehensive task tracking and management.

This module provides API endpoints for monitoring all presentation processing tasks,
including listing tasks, filtering, searching, and retrieving task statistics.
"""

from contextlib import suppress
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Query
from redis.exceptions import RedisError

from slidespeaker.core.progress_utils import compute_step_percentage
from slidespeaker.core.state_manager import state_manager
from slidespeaker.core.task_queue import task_queue

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
    """Get a list of all tasks with optional filtering and pagination."""

    # Helper: safely scan Redis keys with fallback when Redis is unavailable
    async def _safe_scan(pattern: str) -> list[str]:
        try:
            cursor: int = 0
            out: list[str] = []
            while True:
                cursor, batch = await task_queue.redis_client.scan(
                    cursor=cursor, match=pattern, count=500
                )
                out.extend([str(k) for k in batch])
                if cursor == 0:
                    break
            return out
        except (RedisError, TimeoutError, Exception):
            return []

    # Get all task IDs from Redis (gracefully handle Redis down)
    task_keys = await _safe_scan("ss:task:*")
    # Exclude transient cancelled flags
    task_keys = [k for k in task_keys if not str(k).endswith(":cancelled")]

    # Only list task-based states (legacy file-id states are deprecated)
    # Only list task-based states (legacy file-id states are deprecated)
    # Use the same safe scanner on the state manager client
    async def _safe_state_scan(pattern: str) -> list[str]:
        try:
            cursor: int = 0
            out: list[str] = []
            while True:
                cursor, batch = await state_manager.redis_client.scan(
                    cursor=cursor, match=pattern, count=500
                )
                out.extend([str(k) for k in batch])
                if cursor == 0:
                    break
            return out
        except (RedisError, TimeoutError, Exception):
            return []

    task_state_keys = await _safe_state_scan("ss:state:task:*")

    tasks = []

    # Process task queue items
    for task_key in task_keys:
        task_data = await task_queue.redis_client.get(task_key)
        if task_data:
            try:
                task = __import__("json").loads(task_data)
                # Add file_id from kwargs if available
                file_id = task.get("kwargs", {}).get("file_id", "unknown")
                task["file_id"] = file_id

                # Get corresponding state if available
                tid = task.get("task_id")
                state = None
                if isinstance(tid, str) and tid:
                    state = await state_manager.get_state_by_task(tid)
                else:
                    # Fallback (legacy): try file-id (may alias to last-run)
                    state = await state_manager.get_state(file_id)
                if state:
                    # Derive task_type and flags when missing (legacy defaults)
                    gv = state.get("generate_video")
                    gp = state.get("generate_podcast")
                    steps = state.get("steps") or {}
                    derived_type: str | None = state.get("task_type")
                    if (
                        gv is None
                        and gp is None
                        and isinstance(steps, dict)
                        and "compose_podcast" in steps
                    ):
                        gp = True
                        gv = False
                        derived_type = "podcast"
                    if derived_type is None:
                        if gp is True and gv is True:
                            derived_type = "both"
                        elif gp is True:
                            derived_type = "podcast"
                        elif gv is True:
                            derived_type = "video"

                    task["state"] = {
                        "status": state["status"],
                        "current_step": state["current_step"],
                        "filename": state.get("filename"),
                        "source": state.get("source"),
                        "voice_language": state["voice_language"],
                        "subtitle_language": state.get("subtitle_language"),
                        "video_resolution": state.get("video_resolution", "hd"),
                        "generate_avatar": state["generate_avatar"],
                        "generate_subtitles": state["generate_subtitles"],
                        # Prefer explicit; include derived when available
                        "generate_video": gv
                        if gv is not None
                        else state.get("generate_video"),
                        "generate_podcast": gp
                        if gp is not None
                        else state.get("generate_podcast"),
                        "task_type": derived_type
                        if derived_type is not None
                        else state.get("task_type"),
                        "created_at": state["created_at"],
                        "updated_at": state["updated_at"],
                        "errors": state["errors"],
                    }

                tasks.append(task)
            except Exception:
                # Skip malformed tasks
                continue

    # Process state-only items (task-based states without task queue entries)
    for state_key in task_state_keys:
        task_id = str(state_key).replace("ss:state:task:", "")
        # Skip if we already have this task from the queue list
        if any(task.get("task_id") == task_id for task in tasks):
            continue
        st = await state_manager.get_state_by_task(task_id)
        if st:
            fid = st.get("file_id")
            # Derive task_type and flags when missing
            gv = st.get("generate_video")
            gp = st.get("generate_podcast")
            steps = st.get("steps") or {}
            derived_type2: str | None = st.get("task_type")
            if (
                gv is None
                and gp is None
                and isinstance(steps, dict)
                and "compose_podcast" in steps
            ):
                gp = True
                gv = False
                derived_type2 = "podcast"
            if derived_type2 is None:
                if gp is True and gv is True:
                    derived_type2 = "both"
                elif gp is True:
                    derived_type2 = "podcast"
                elif gv is True:
                    derived_type2 = "video"
            tasks.append(
                {
                    "task_id": task_id,
                    "file_id": fid,
                    "task_type": "process_presentation",
                    "status": st.get("status"),
                    "created_at": st.get("created_at"),
                    "updated_at": st.get("updated_at"),
                    "state": {
                        "status": st.get("status"),
                        "current_step": st.get("current_step"),
                        "source": st.get("source"),
                        "voice_language": st.get("voice_language"),
                        "subtitle_language": st.get("subtitle_language"),
                        "video_resolution": st.get("video_resolution", "hd"),
                        "generate_avatar": st.get("generate_avatar"),
                        "generate_subtitles": st.get("generate_subtitles"),
                        "generate_video": gv
                        if gv is not None
                        else st.get("generate_video"),
                        "generate_podcast": gp
                        if gp is not None
                        else st.get("generate_podcast"),
                        "task_type": derived_type2
                        if derived_type2 is not None
                        else st.get("task_type"),
                        "created_at": st.get("created_at"),
                        "updated_at": st.get("updated_at"),
                        "errors": st.get("errors", []),
                    },
                    "kwargs": {
                        "file_id": fid,
                        "file_ext": st.get("file_ext"),
                        "filename": st.get("filename"),
                        "source": st.get("source"),
                        "voice_language": st.get("voice_language"),
                        "subtitle_language": st.get("subtitle_language"),
                        "video_resolution": st.get("video_resolution", "hd"),
                        "generate_avatar": st.get("generate_avatar"),
                        "generate_subtitles": st.get("generate_subtitles"),
                        "generate_video": st.get("generate_video"),
                        "generate_podcast": st.get("generate_podcast"),
                        "task_type": st.get("task_type"),
                    },
                }
            )

    # Apply status filter if provided
    if status:
        tasks = [task for task in tasks if task["status"] == status]

    # Sort tasks
    reverse = str(sort_order).lower() == "desc"
    try:
        tasks.sort(key=lambda x: x.get(str(sort_by), ""), reverse=reverse)
    except KeyError:
        # Fallback to created_at if sort field doesn't exist
        tasks.sort(key=lambda x: x.get("created_at", ""), reverse=reverse)

    # Apply pagination
    total_tasks = len(tasks)
    paginated_tasks = tasks[offset : offset + limit]

    return {
        "tasks": paginated_tasks,
        "total": total_tasks,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total_tasks,
    }


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
    query: str = Query(..., description="Search query for file ID or task properties"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
) -> dict[str, Any]:
    """Search for tasks by file ID or other properties."""

    # Get all tasks
    all_tasks_result = await get_tasks(
        status=None, limit=1000, offset=0, sort_by="created_at", sort_order="desc"
    )  # Get all tasks for searching
    all_tasks = all_tasks_result["tasks"]

    # Search in file IDs and task properties
    matching_tasks = []
    query_lower = query.lower()

    for task in all_tasks:
        # Search in file_id
        if query_lower in task.get("file_id", "").lower():
            matching_tasks.append(task)
            continue

        # Search in state properties
        state = task.get("state", {})
        if query_lower in state.get("status", "").lower():
            matching_tasks.append(task)
            continue

        if query_lower in state.get("voice_language", "").lower():
            matching_tasks.append(task)
            continue

        if query_lower in state.get("current_step", "").lower():
            matching_tasks.append(task)
            continue

    # Limit results
    matching_tasks = matching_tasks[:limit]

    return {
        "tasks": matching_tasks,
        "query": query,
        "total_found": len(matching_tasks),
    }


@router.get("/tasks/statistics")
async def get_task_statistics() -> dict[str, Any]:
    """Get comprehensive statistics about all tasks."""

    # Get all tasks
    all_tasks_result = await get_tasks(
        status=None, limit=10000, offset=0, sort_by="created_at", sort_order="desc"
    )  # Get all tasks for stats
    all_tasks = all_tasks_result["tasks"]

    total_tasks = len(all_tasks)

    if total_tasks == 0:
        return {
            "total_tasks": 0,
            "status_breakdown": {},
            "language_stats": {},
            "recent_activity": {
                "last_24h": 0,
                "last_7d": 0,
                "last_30d": 0,
            },
            "processing_stats": {
                "avg_processing_time": None,
                "success_rate": 0,
                "failed_rate": 0,
            },
        }

    # Status breakdown
    status_breakdown: dict[str, int] = {}
    for task in all_tasks:
        status = task["status"]
        status_breakdown[status] = status_breakdown.get(status, 0) + 1

    # Language statistics
    language_stats: dict[str, int] = {}
    for task in all_tasks:
        state = task.get("state", {})
        voice_lang = state.get("voice_language", "unknown")
        subtitle_lang = state.get("subtitle_language", "unknown")

        language_stats[voice_lang] = language_stats.get(voice_lang, 0) + 1
        if subtitle_lang != voice_lang:
            language_stats[subtitle_lang] = language_stats.get(subtitle_lang, 0) + 1

    # Recent activity
    now = datetime.now()
    last_24h = sum(
        1
        for task in all_tasks
        if datetime.fromisoformat(task.get("created_at", "").replace("Z", "+00:00"))
        > now - timedelta(days=1)
    )
    last_7d = sum(
        1
        for task in all_tasks
        if datetime.fromisoformat(task.get("created_at", "").replace("Z", "+00:00"))
        > now - timedelta(days=7)
    )
    last_30d = sum(
        1
        for task in all_tasks
        if datetime.fromisoformat(task.get("created_at", "").replace("Z", "+00:00"))
        > now - timedelta(days=30)
    )

    # Processing statistics
    completed_tasks = [task for task in all_tasks if task["status"] == "completed"]
    failed_tasks = [task for task in all_tasks if task["status"] == "failed"]

    success_rate = len(completed_tasks) / total_tasks * 100 if total_tasks > 0 else 0
    failed_rate = len(failed_tasks) / total_tasks * 100 if total_tasks > 0 else 0

    # Calculate average processing time for completed tasks
    avg_processing_time = None
    if completed_tasks:
        processing_times = []
        for task in completed_tasks:
            try:
                created = datetime.fromisoformat(
                    task.get("created_at", "").replace("Z", "+00:00")
                )
                updated = datetime.fromisoformat(
                    task.get("updated_at", "").replace("Z", "+00:00")
                )
                processing_time = (updated - created).total_seconds() / 60  # minutes
                processing_times.append(processing_time)
            except Exception:
                continue

        if processing_times:
            avg_processing_time = sum(processing_times) / len(processing_times)

    return {
        "total_tasks": total_tasks,
        "status_breakdown": status_breakdown,
        "language_stats": language_stats,
        "recent_activity": {
            "last_24h": last_24h,
            "last_7d": last_7d,
            "last_30d": last_30d,
        },
        "processing_stats": {
            "avg_processing_time_minutes": avg_processing_time,
            "success_rate": round(success_rate, 2),
            "failed_rate": round(failed_rate, 2),
        },
    }


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
                    "voice_language": state["voice_language"],
                    "subtitle_language": state.get("subtitle_language"),
                    "generate_avatar": state["generate_avatar"],
                    "generate_subtitles": state["generate_subtitles"],
                },
                "state": state,
            }

    if not task:
        return {
            "error": "Task not found",
            "task_id": task_id,
        }

    # Enrich with detailed state information
    file_id = task.get("kwargs", {}).get("file_id", "unknown")
    if file_id != "unknown":
        state = await state_manager.get_state(file_id)
        if state:
            task["detailed_state"] = state

            # Add step completion percentage
            task["completion_percentage"] = compute_step_percentage(state)

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


@router.delete("/tasks/{task_id}/purge")
async def purge_task(task_id: str) -> dict[str, Any]:
    """Permanently delete a task and its state from the system.

    This removes the task entry, queue references, cancellation flags, and associated state.
    """
    # Fetch task to get file_id, but proceed even if not found
    task = await task_queue.get_task(task_id)
    file_id = task.get("kwargs", {}).get("file_id") if task else None

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

    try:
        # Remove from queue (all occurrences)
        try:
            removed_count = await task_queue.redis_client.lrem(
                task_queue.queue_key,
                0,
                task_id,  # type: ignore
            )
            removed["queue"] = int(removed_count) if removed_count is not None else 0
        except Exception:
            pass

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

        # Remove task from file's multi-task set and decide whether to delete file state
        remaining = 0
        if file_id and file2tasks_set_key:
            try:
                await state_manager.redis_client.srem(file2tasks_set_key, task_id)  # type: ignore
                left = await state_manager.redis_client.scard(file2tasks_set_key)  # type: ignore
                remaining = int(left or 0)
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
