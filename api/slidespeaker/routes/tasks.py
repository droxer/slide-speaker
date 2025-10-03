"""
Task management routes for handling task operations.

This module provides API endpoints for retrieving task status and canceling tasks.
It interfaces with the Redis task queue system to manage presentation processing tasks.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from slidespeaker.core.task_queue import task_queue
from slidespeaker.utils.auth import extract_user_id, require_authenticated_user

router = APIRouter(
    prefix="/api",
    tags=["tasks"],
    dependencies=[Depends(require_authenticated_user)],
)


@router.get("/task/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: Annotated[dict[str, Any], Depends(require_authenticated_user)],
) -> dict[str, Any]:
    """Get task status by ID."""
    owner_id = extract_user_id(current_user)
    if not owner_id:
        raise HTTPException(status_code=403, detail="user session missing id")

    task_status = await task_queue.get_task(task_id)
    if task_status:
        task_owner = task_status.get("owner_id")
        if task_owner and task_owner != owner_id:
            raise HTTPException(status_code=404, detail="Task not found")
    if not task_status or not task_status.get("owner_id"):
        from slidespeaker.repository.task import get_task as db_get_task

        row = await db_get_task(task_id)
        if not row or row.get("owner_id") != owner_id:
            raise HTTPException(status_code=404, detail="Task not found")
        if not task_status:
            return row
        task_status["owner_id"] = owner_id

    return task_status


@router.post("/task/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    current_user: Annotated[dict[str, Any], Depends(require_authenticated_user)],
) -> dict[str, str]:
    """Cancel a task."""
    owner_id = extract_user_id(current_user)
    if not owner_id:
        raise HTTPException(status_code=403, detail="user session missing id")

    from slidespeaker.repository.task import get_task as db_get_task

    row = await db_get_task(task_id)
    if not row or row.get("owner_id") != owner_id:
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
