"""
Task management routes for handling task operations.

This module provides API endpoints for retrieving task status and canceling tasks.
It interfaces with the Redis task queue system to manage presentation processing tasks.
"""

import json
from contextlib import suppress
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from loguru import logger
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from slidespeaker.auth import extract_user_id, require_authenticated_user
from slidespeaker.core.monitoring import monitor_endpoint
from slidespeaker.core.progress_utils import compute_step_percentage
from slidespeaker.core.state_manager import state_manager
from slidespeaker.core.task_queue import task_queue
from slidespeaker.jobs.file_purger import file_purger
from slidespeaker.repository.task import (
    delete_task as db_delete_task,
)
from slidespeaker.repository.task import (
    get_statistics as db_get_statistics,
)
from slidespeaker.repository.task import (
    get_task as db_get_task,
)
from slidespeaker.repository.task import (
    list_tasks as db_list_tasks,
)

# Create a rate limiter for this router
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(
    prefix="/api",
    tags=["tasks"],
    dependencies=[Depends(require_authenticated_user)],
)


class TaskRetryRequest(BaseModel):
    step: str | None = None


@router.get("/tasks/{task_id}/status")
@limiter.limit("30/minute")  # Limit to 30 task status requests per minute per IP
@monitor_endpoint
async def get_task_status(
    request: Request,
    task_id: str,
    current_user: Annotated[dict[str, Any], Depends(require_authenticated_user)],
) -> dict[str, Any]:
    """Get task status by ID."""
    user_id = extract_user_id(current_user)
    if not user_id:
        raise HTTPException(status_code=403, detail="user session missing id")

    task_status = await task_queue.get_task(task_id)
    if task_status:
        task_owner = task_status.get("user_id")
        if task_owner and task_owner != user_id:
            raise HTTPException(status_code=404, detail="Task not found")
    if not task_status or not task_status.get("user_id"):
        from slidespeaker.repository.task import get_task as db_get_task

        row = await db_get_task(task_id)
        if not row or row.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail="Task not found")
        if not task_status:
            return row
        task_status["user_id"] = user_id

    return task_status


@router.post("/tasks/{task_id}/cancel")
@limiter.limit("10/minute")  # Limit to 10 task cancellations per minute per IP
@monitor_endpoint
async def cancel_task(
    request: Request,
    task_id: str,
    current_user: Annotated[dict[str, Any], Depends(require_authenticated_user)],
) -> dict[str, str]:
    """Cancel a task."""
    user_id = extract_user_id(current_user)
    if not user_id:
        raise HTTPException(status_code=403, detail="user session missing id")

    from slidespeaker.repository.task import get_task as db_get_task

    row = await db_get_task(task_id)
    if not row or row.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        success = await task_queue.cancel_task(task_id)
        if success:
            return {"message": "Task cancelled successfully"}
        raise HTTPException(
            status_code=400,
            detail="Task cannot be cancelled (already completed or not found)",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to cancel task: {str(e)}"
        ) from e


@router.post("/tasks/{task_id}/retry")
@limiter.limit("10/minute")
@monitor_endpoint
async def retry_task_endpoint(
    request: Request,
    task_id: str,
    payload: TaskRetryRequest,
    current_user: Annotated[dict[str, Any], Depends(require_authenticated_user)],
) -> dict[str, Any]:
    """Retry a failed task from a specific step."""
    user_id = extract_user_id(current_user)
    if not user_id:
        raise HTTPException(status_code=403, detail="user session missing id")

    row = await db_get_task(task_id)
    if not row or row.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Task not found")

    state = await state_manager.get_state_by_task(task_id)
    if not state:
        file_id = (
            row.get("file_id")
            or row.get("upload_id")
            or (row.get("kwargs") or {}).get("file_id")
        )
        if isinstance(file_id, str) and file_id:
            # Fallback to file-scoped state when task alias is missing
            state = await state_manager.get_state(file_id)
            if state:
                # Re-bind for future lookups; ignore failures so we can continue gracefully
                with suppress(Exception):
                    await state_manager.bind_task(file_id, task_id)
    if not state:
        raise HTTPException(status_code=400, detail="Task state unavailable for retry")

    if state.get("status") != "failed":
        raise HTTPException(
            status_code=400, detail="Retry is only allowed for failed tasks"
        )

    steps = state.get("steps") or {}
    if not isinstance(steps, dict) or len(steps) == 0:
        raise HTTPException(
            status_code=400, detail="Task does not contain resumable steps"
        )

    requested_step = (payload.step or "").strip() if payload.step else None
    resume_step: str | None = None

    if requested_step and requested_step in steps:
        resume_step = requested_step
    else:
        errors = state.get("errors") or []
        if isinstance(errors, list):
            for entry in reversed(errors):
                step_name = entry.get("step")
                if isinstance(step_name, str) and step_name in steps:
                    resume_step = step_name
                    break
        if not resume_step:
            for step_name, step_state in steps.items():
                if (
                    isinstance(step_state, dict)
                    and step_state.get("status") == "failed"
                ):
                    resume_step = step_name
                    break

    if not resume_step:
        current_step = state.get("current_step")
        if isinstance(current_step, str) and current_step in steps:
            resume_step = current_step

    if not resume_step:
        first_step = next(iter(steps.keys()), None)
        if isinstance(first_step, str) and first_step:
            resume_step = first_step

    if not resume_step:
        raise HTTPException(
            status_code=400,
            detail="Unable to determine a step to resume from for this task",
        )

    reset_state = await state_manager.reset_steps_from_task(task_id, resume_step)
    if not reset_state:
        raise HTTPException(
            status_code=400, detail="Failed to reset task steps for retry"
        )

    enqueued = await task_queue.enqueue_existing_task(task_id)
    if not enqueued:
        raise HTTPException(
            status_code=400, detail="Task could not be enqueued for retry"
        )

    return {
        "message": "Task retry queued",
        "step": resume_step,
        "status": reset_state.get("status", "processing"),
    }


@router.delete("/tasks/{task_id}/delete")
@limiter.limit("10/minute")  # Limit to 10 task deletions per minute per IP
@monitor_endpoint
async def delete_task(
    request: Request,
    task_id: str,
    current_user: Annotated[dict[str, Any], Depends(require_authenticated_user)],
) -> dict[str, str]:
    """Delete a task and its associated files from database and storage."""
    logger.info(f"delete_task called with task_id: {task_id}")
    user_id = extract_user_id(current_user)
    logger.info(f"User ID: {user_id}")
    if not user_id:
        logger.error("User session missing ID")
        raise HTTPException(status_code=403, detail="user session missing id")

    # Verify task exists and belongs to user
    logger.info(f"Fetching task {task_id} from database")
    row = await db_get_task(task_id)
    logger.info(f"Database row for task {task_id}: {row}")
    if not row or row.get("user_id") != user_id:
        logger.error(f"Task {task_id} not found or doesn't belong to user {user_id}")
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        # Get the file_id to delete associated files
        file_id = row.get("file_id")
        logger.info(f"File ID for task {task_id}: {file_id}")

        collected_storage_keys: set[str] = set()
        collected_local_paths: set[str] = set()
        if file_id:
            try:
                (
                    collected_storage_keys,
                    collected_local_paths,
                ) = await file_purger.collect_artifacts(
                    file_id,
                    task_id=task_id,
                    file_ext=row.get("file_ext"),
                )
            except Exception as exc:
                logger.warning(
                    "Failed to collect artifacts prior to purge (task_id=%s, file_id=%s): %s",
                    task_id,
                    file_id,
                    exc,
                )

        # Step 1: Cancel the task in the queue first
        logger.info(f"Cancelling task {task_id} in queue")
        try:
            await task_queue.update_task_status(task_id, "cancelled")
            logger.info(f"Successfully cancelled task {task_id} in queue")
        except Exception as e:
            logger.error(f"Error cancelling task {task_id} in queue: {e}")
            # Don't fail the whole operation if queue cancellation fails

        # Step 2: Delete task from database
        logger.info(f"Attempting to delete task {task_id} from database")
        try:
            await db_delete_task(task_id)
            logger.info(f"Successfully deleted task {task_id} from database")
        except Exception as e:
            logger.error(f"Error deleting task {task_id} from database: {e}")
            raise

        # Step 3: Remove task from Redis queue and clean up all associated Redis data
        try:
            logger.info(
                f"Removing task {task_id} from Redis queue and cleaning up associated data"
            )

            # Resolve file_id via DB first, then queue/state (same as in purge_task)
            resolved_file_id = await _resolve_file_id(task_id)
            logger.info(f"Resolved file_id for task {task_id}: {resolved_file_id}")

            # Build keys (same as in purge_task)
            task_key = f"{task_queue.task_prefix}:{task_id}"
            cancellation_key = f"{task_queue.task_prefix}:{task_id}:cancelled"
            state_key = f"ss:state:{resolved_file_id}" if resolved_file_id else None
            task_state_key = f"ss:state:task:{task_id}"
            task2file_key = f"ss:task2file:{task_id}"
            file2task_key = (
                f"ss:file2task:{resolved_file_id}" if resolved_file_id else None
            )
            file2tasks_set_key = (
                f"ss:file2tasks:{resolved_file_id}" if resolved_file_id else None
            )

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
                resolved_file_id,
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

            logger.info(
                f"Successfully removed task {task_id} from Redis. Removed items: {removed}"
            )
        except Exception as e:
            logger.error(f"Error removing task {task_id} from Redis: {e}")
            # Don't fail the whole operation if Redis cleanup fails

        # Step 4: Trigger asynchronous deletion from storage
        if file_id:
            try:
                await file_purger.enqueue_file_purge(
                    file_id,
                    target_task_id=task_id,
                    file_ext=row.get("file_ext"),
                    storage_keys=collected_storage_keys,
                    local_paths=collected_local_paths,
                )
                logger.info(f"Enqueued file purge for file_id: {file_id}")
            except Exception as e:
                logger.error(f"Error enqueuing file purge for task {task_id}: {e}")
                # Don't fail the whole operation if file purge enqueue fails

        logger.info(f"Successfully completed deletion of task {task_id}")
        return {"message": f"Task {task_id} deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete task: {str(e)}"
        ) from e


def _filter_sensitive_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Filter out sensitive information from kwargs before returning in API responses."""
    filtered = kwargs.copy()
    # Remove sensitive fields that shouldn't be exposed to clients
    filtered.pop("file_path", None)
    return filtered


def _serialize_task(row: Any) -> dict[str, Any]:
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


@router.get("/tasks")
@limiter.limit("30/minute")  # Limit to 30 task list requests per minute per IP
@monitor_endpoint
async def get_tasks(
    request: Request,
    *,
    status: str | None = Query(None, description="Filter by task status"),
    limit: int = Query(
        50, ge=1, le=1000, description="Maximum number of tasks to return"
    ),
    offset: int = Query(0, ge=0, description="Number of tasks to skip"),
    sort_by: str = Query(
        "created_at", description="Sort field (created_at, updated_at, status)"
    ),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    current_user: Annotated[dict[str, Any], Depends(require_authenticated_user)],
) -> dict[str, Any]:
    """DB-backed task list. Uses repository; no Redis scanning."""
    """DB-backed task list. Uses repository; no Redis scanning."""

    user_id = extract_user_id(current_user)
    if not user_id:
        return {
            "tasks": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "has_more": False,
        }

    db_res = await db_list_tasks(
        limit=limit, offset=offset, status=status, user_id=user_id
    )
    return {
        "tasks": db_res["tasks"],
        "total": db_res["total"],
        "limit": limit,
        "offset": offset,
        "has_more": (db_res["total"] > offset + limit),
    }


@router.get("/tasks/search")
@limiter.limit("30/minute")  # Limit to 30 search requests per minute per IP
@monitor_endpoint
async def search_tasks(
    request: Request,
    *,
    query: str = Query(
        ...,
        description="Search query for task_id, file_id, status, task_type, or kwargs",
    ),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    current_user: Annotated[dict[str, Any], Depends(require_authenticated_user)],
) -> dict[str, Any]:
    """DB-backed search across basic fields. No Redis usage."""

    user_id = extract_user_id(current_user)
    if not user_id:
        return {"tasks": [], "query": query, "total_found": 0}

    # Try to get from cache first (cache key based on user and query)
    cache_key = f"search_tasks:{user_id}:{query}:{limit}"
    with suppress(Exception):
        cached_result = await task_queue.redis_client.get(cache_key)
        if cached_result:
            return json.loads(cached_result)

    # Search in DB with optimized query using the repository function
    from sqlalchemy import select

    from slidespeaker.configs.db import get_session
    from slidespeaker.core.models import TaskRow, UploadRow

    async with get_session() as s:
        # Create a more efficient search query with proper indexing
        stmt = (
            select(TaskRow)
            .join(TaskRow.upload)
            .where(UploadRow.user_id == user_id)
            .where(TaskRow.id.ilike(f"%{query}%"))
            .limit(limit)
        )

        result = await s.execute(stmt)
        rows = result.scalars().all()

        matches = [_serialize_task(r) for r in rows]

        response = {"tasks": matches, "query": query, "total_found": len(matches)}

        # Cache for 2 minutes
        with suppress(Exception):
            await task_queue.redis_client.setex(cache_key, 120, json.dumps(response))

        return response


@router.get("/tasks/statistics")
@limiter.limit("30/minute")  # Limit to 30 statistics requests per minute per IP
@monitor_endpoint
async def get_task_statistics(
    request: Request,
    current_user: Annotated[dict[str, Any], Depends(require_authenticated_user)],
) -> dict[str, Any]:
    """Get comprehensive statistics about all tasks (DB only)."""

    user_id = extract_user_id(current_user)
    if not user_id:
        return {
            "total_tasks": 0,
            "status_breakdown": {},
            "language_stats": {},
            "recent_activity": {"last_24h": 0, "last_7d": 0, "last_30d": 0},
            "processing_stats": {
                "avg_processing_time_minutes": None,
                "success_rate": 0.0,
                "failed_rate": 0.0,
            },
        }

    return await db_get_statistics(user_id=user_id)


@router.get("/tasks/{task_id}")
@limiter.limit("30/minute")  # Limit to 30 task detail requests per minute per IP
@monitor_endpoint
async def get_task_details(
    request: Request,
    task_id: str,
    current_user: Annotated[dict[str, Any], Depends(require_authenticated_user)],
) -> dict[str, Any]:
    """Get detailed information about a specific task.

    For running tasks: Uses Redis state as primary source with detailed step information.
    For completed/failed/cancelled tasks: Uses database as primary source, Redis state as enhancement if available.
    Redis state has 24-hour TTL, so completed tasks gracefully degrade to database-only information."""

    user_id = extract_user_id(current_user)
    if not user_id:
        raise HTTPException(status_code=403, detail="user session missing id")

    # Try to get from task queue first
    task = await task_queue.get_task(task_id)

    row = await db_get_task(task_id)
    if not row or row.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Task not found")

    if task:
        task_owner = task.get("user_id")
        if task_owner and task_owner != user_id:
            raise HTTPException(status_code=404, detail="Task not found")
        task.setdefault("user_id", user_id)

    if not task and task_id.startswith("state_"):
        # Check if it's a state-only task (format: state_{file_id})
        file_id = task_id.replace("state_", "")
        state = await state_manager.get_state(file_id)
        if state:
            st_owner = state.get("user_id")
            if isinstance(st_owner, str) and st_owner and st_owner != user_id:
                raise HTTPException(status_code=404, detail="Task not found")
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
        # DB fallback: reconstruct from DB + state (for completed tasks)
        file_id = str(row.get("file_id")) if row.get("file_id") is not None else ""

        # For completed/failed/cancelled tasks, try Redis state as enhancement only
        st = None
        if file_id and row.get("status") in ["completed", "failed", "cancelled"]:
            st = await state_manager.get_state(file_id)
            if st:
                st_owner = st.get("user_id")
                if isinstance(st_owner, str) and st_owner and st_owner != user_id:
                    st = None  # Invalid state ownership, ignore

        # Filter sensitive information from kwargs
        filtered_kwargs = _filter_sensitive_kwargs(row.get("kwargs") or {})

        return {
            "task_id": row.get("task_id"),
            "file_id": file_id,
            "task_type": row.get("task_type"),
            "status": row.get("status"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
            "kwargs": filtered_kwargs,
            "source_type": (st or {}).get("source_type")
            or (st or {}).get("source")
            or (filtered_kwargs.get("source_type")),
            "state": st,
            "completion_percentage": compute_step_percentage(st)
            if st
            else 100,  # Assume 100% for completed tasks
            # without state
            "user_id": user_id,
        }

    # Enrich with detailed state information (for running tasks or recently completed)
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


async def _resolve_file_id(task_id: str) -> str | None:
    """Resolve file_id via DB first, then queue/state"""
    file_id: str | None = None
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
@limiter.limit("10/minute")  # Limit to 10 task purges per minute per IP
@monitor_endpoint
async def purge_task(
    task_id: str,
    request: Request,
    current_user: Annotated[dict[str, Any], Depends(require_authenticated_user)],
) -> dict[str, Any]:
    """Permanently delete a task and its state from the system.

    This removes the task entry, queue references, cancellation flags, and associated state.
    """
    user_id = extract_user_id(current_user)
    if not user_id:
        raise HTTPException(status_code=403, detail="user session missing id")

    row = await db_get_task(task_id)
    if not row or row.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        # Resolve file_id via DB first, then queue/state
        file_id = await _resolve_file_id(task_id)

        collected_storage_keys: set[str] = set()
        collected_local_paths: set[str] = set()
        if file_id:
            try:
                (
                    collected_storage_keys,
                    collected_local_paths,
                ) = await file_purger.collect_artifacts(
                    file_id,
                    task_id=task_id,
                    file_ext=row.get("file_ext"),
                )
            except Exception as exc:
                logger.warning(
                    "Failed to collect artifacts prior to purge (task_id=%s, file_id=%s): %s",
                    task_id,
                    file_id,
                    exc,
                )

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
        try:
            await db_delete_task(task_id)
        except Exception as e:
            logger.error(
                f"Error deleting task {task_id} from database during purge: {e}"
            )
            # Don't fail the whole operation if DB deletion fails

        # Enqueue file purge task if this was the last task for the file
        if file_id and remaining == 0:
            try:
                # Import here to avoid circular imports
                await file_purger.enqueue_file_purge(
                    file_id,
                    target_task_id=task_id,
                    file_ext=row.get("file_ext"),
                    storage_keys=collected_storage_keys,
                    local_paths=collected_local_paths,
                )
            except Exception as e:
                logger.error(f"Error enqueuing file purge for file_id {file_id}: {e}")

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
