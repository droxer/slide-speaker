"""
Task monitoring routes for comprehensive task tracking and management.

This module provides API endpoints for monitoring all presentation processing tasks,
including listing tasks, filtering, searching, and retrieving task statistics.
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Query

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

    # Get all task IDs from Redis
    task_keys = await task_queue.redis_client.keys("ss:task:*")
    state_keys = await state_manager.redis_client.keys("ss:state:*")

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
                state = await state_manager.get_state(file_id)
                if state:
                    task["state"] = {
                        "status": state["status"],
                        "current_step": state["current_step"],
                        "filename": state.get("filename"),
                        "voice_language": state["voice_language"],
                        "subtitle_language": state.get("subtitle_language"),
                        "generate_avatar": state["generate_avatar"],
                        "generate_subtitles": state["generate_subtitles"],
                        "created_at": state["created_at"],
                        "updated_at": state["updated_at"],
                        "errors": state["errors"],
                    }

                tasks.append(task)
            except Exception:
                # Skip malformed tasks
                continue

    # Process state-only items (tasks that might not have queue entries)
    for state_key in state_keys:
        file_id = state_key.replace("ss:state:", "")

        # Skip if we already have this task from the queue
        if any(task.get("file_id") == file_id for task in tasks):
            continue

        state = await state_manager.get_state(file_id)
        if state:
            # Create a synthetic task entry for state-only items
            tasks.append(
                {
                    "task_id": f"state_{file_id}",
                    "file_id": file_id,
                    "task_type": "process_presentation",
                    "status": state["status"],
                    "created_at": state["created_at"],
                    "updated_at": state["updated_at"],
                    "state": {
                        "status": state["status"],
                        "current_step": state["current_step"],
                        "voice_language": state["voice_language"],
                        "subtitle_language": state.get("subtitle_language"),
                        "generate_avatar": state["generate_avatar"],
                        "generate_subtitles": state["generate_subtitles"],
                        "created_at": state["created_at"],
                        "updated_at": state["updated_at"],
                        "errors": state["errors"],
                    },
                    "kwargs": {
                        "file_id": file_id,
                        "file_ext": state["file_ext"],
                        "filename": state.get("filename"),
                        "voice_language": state["voice_language"],
                        "subtitle_language": state.get("subtitle_language"),
                        "generate_avatar": state["generate_avatar"],
                        "generate_subtitles": state["generate_subtitles"],
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
            total_steps = len(
                [
                    step
                    for step in state["steps"].values()
                    if step["status"] != "skipped"
                ]
            )
            completed_steps = sum(
                1 for step in state["steps"].values() if step["status"] == "completed"
            )
            task["completion_percentage"] = (
                int((completed_steps / total_steps) * 100) if total_steps > 0 else 0
            )

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

    # Update state if file_id is available
    file_id = task.get("kwargs", {}).get("file_id")
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

        # Delete state key
        if state_key:
            try:
                del_count = await state_manager.redis_client.delete(state_key)
                removed["state"] = int(del_count) if del_count is not None else 0
            except Exception:
                pass

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
