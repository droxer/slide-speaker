"""
Progress tracking routes for monitoring processing status.

This module provides API endpoints for retrieving detailed progress information
about presentation processing tasks, including current step, status, and errors.
"""

from typing import Any

from fastapi import APIRouter, HTTPException

from slidespeaker.core.state_manager import state_manager

router = APIRouter(prefix="/api", tags=["progress"])


# Note: file-id progress route fully removed. Use /api/tasks/{task_id}/progress.


def _progress_from_state(state: dict[str, Any] | None) -> dict[str, Any]:
    if not state:
        return {
            "status": "not_found",
            "message": "Task not found or processing not started",
            "progress": 0,
            "current_step": "unknown",
            "steps": {},
        }
    # Compute percentage based on non-skipped steps
    steps = state.get("steps", {}) or {}
    total_steps = len([s for s in steps.values() if s.get("status") != "skipped"])
    completed_steps = sum(1 for s in steps.values() if s.get("status") == "completed")
    progress_percentage = (
        int((completed_steps / total_steps) * 100) if total_steps > 0 else 0
    )
    return {
        "status": state.get("status", "unknown"),
        "progress": progress_percentage,
        "current_step": state.get("current_step", "unknown"),
        "steps": steps,
        "errors": state.get("errors", []),
        "filename": state.get("filename"),
        "file_ext": state.get("file_ext"),
        "voice_language": state.get("voice_language"),
        "subtitle_language": state.get(
            "subtitle_language", state.get("voice_language")
        ),
        "created_at": state.get("created_at"),
        "updated_at": state.get("updated_at"),
    }


@router.get("/tasks/{task_id}/progress")
async def get_progress_by_task(task_id: str) -> dict[str, Any]:
    """Task-based progress endpoint resolving state by task-id (task-first)."""
    from slidespeaker.core.task_queue import task_queue

    # Prefer task-based state alias
    st = await state_manager.get_state_by_task(task_id)
    if st and isinstance(st, dict):
        return _progress_from_state(st)

    # Fallback to task queue mapping -> file_id -> state
    task = await task_queue.get_task(task_id)
    if not task:
        # Support state-only ids (state_{file_id})
        if task_id.startswith("state_"):
            file_id = task_id.replace("state_", "")
            st2 = await state_manager.get_state(file_id)
            return _progress_from_state(st2)
        raise HTTPException(status_code=404, detail="Task not found")
    task_file_id = (task.get("kwargs") or {}).get("file_id") or task.get("file_id")
    if not task_file_id:
        raise HTTPException(status_code=404, detail="File not found for task")
    st2 = await state_manager.get_state(task_file_id)
    return _progress_from_state(st2)
