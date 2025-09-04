"""Task management routes for handling task operations."""

from typing import Any

from fastapi import APIRouter, HTTPException
from loguru import logger

from slidespeaker.core.task_queue import task_queue

router = APIRouter(prefix="/api", tags=["tasks"])


@router.get("/task/{task_id}")
async def get_task_status(task_id: str) -> dict[str, Any]:
    """Get task status by ID."""
    task_status = await task_queue.get_task(task_id)
    if not task_status:
        raise HTTPException(status_code=404, detail="Task not found")

    return task_status


@router.post("/task/{task_id}/cancel")
async def cancel_task(task_id: str) -> dict[str, str]:
    """Cancel a task."""
    try:
        success = await task_queue.cancel_task(task_id)
        if success:
            return {"message": "Task cancelled successfully"}
        else:
            raise HTTPException(
                status_code=400,
                detail="Task cannot be cancelled (already completed or not found)",
            )
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to cancel task: {str(e)}"
        ) from e
