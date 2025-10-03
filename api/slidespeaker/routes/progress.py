"""
Progress tracking routes for monitoring processing status.

This module provides API endpoints for retrieving detailed progress information
about presentation processing tasks, including current step, status, and errors.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from slidespeaker.auth import extract_user_id, require_authenticated_user
from slidespeaker.core.progress_utils import compute_step_percentage
from slidespeaker.core.state_manager import state_manager

router = APIRouter(
    prefix="/api",
    tags=["progress"],
    dependencies=[Depends(require_authenticated_user)],
)


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
    progress_percentage = compute_step_percentage(state)
    return {
        "status": state.get("status", "unknown"),
        "progress": progress_percentage,
        "current_step": state.get("current_step", "unknown"),
        "steps": state.get("steps", {}) or {},
        "errors": state.get("errors", []),
        "filename": state.get("filename"),
        "file_ext": state.get("file_ext"),
        "source_type": state.get("source_type") or state.get("source"),
        "voice_language": state.get("voice_language"),
        "subtitle_language": state.get(
            "subtitle_language", state.get("voice_language")
        ),
        "generate_podcast": state.get("generate_podcast", False),
        "generate_video": state.get("generate_video", True),
        "created_at": state.get("created_at"),
        "updated_at": state.get("updated_at"),
    }


@router.get("/tasks/{task_id}/progress")
async def get_progress_by_task(
    task_id: str,
    current_user: Annotated[dict[str, Any], Depends(require_authenticated_user)],
) -> dict[str, Any]:
    """Task-based progress endpoint resolving state by task-id (task-first)."""
    from slidespeaker.core.task_queue import task_queue
    from slidespeaker.repository.task import get_task as db_get_task

    owner_id = extract_user_id(current_user)
    if not owner_id:
        raise HTTPException(status_code=403, detail="user session missing id")

    db_row = await db_get_task(task_id)
    if not db_row or db_row.get("owner_id") != owner_id:
        raise HTTPException(status_code=404, detail="Task not found")

    # Prefer task-based state alias
    st = await state_manager.get_state_by_task(task_id)
    if not isinstance(st, dict):
        st = None
    if st is None and db_row and db_row.get("file_id"):
        st = await state_manager.get_state(str(db_row["file_id"]))
    if st and isinstance(st, dict):
        st_owner = st.get("owner_id")
        if isinstance(st_owner, str) and st_owner and st_owner != owner_id:
            raise HTTPException(status_code=404, detail="Task not found")
        result = _progress_from_state(st)
        # Attach task_type from DB if available and derive generate_* for compatibility
        if db_row and db_row.get("task_type"):
            tt = (db_row["task_type"] or "").lower()
            result["task_type"] = tt
            # Derive legacy flags for existing clients
            result["generate_video"] = tt in ("video", "both")
            result["generate_podcast"] = tt in ("podcast", "both")
            # For podcast tasks, prefer DB.subtitle_language as transcript language setting
            if tt == "podcast":
                db_sub = db_row.get("subtitle_language")
                if db_sub:
                    result["subtitle_language"] = db_sub
        return result

    # Fallback to task queue mapping -> file_id -> state
    task = await task_queue.get_task(task_id)
    if not task:
        # Support state-only ids (state_{file_id})
        if task_id.startswith("state_"):
            file_id = task_id.replace("state_", "")
            st2 = await state_manager.get_state(file_id)
            if st2:
                st_owner = st2.get("owner_id")
                if isinstance(st_owner, str) and st_owner and st_owner != owner_id:
                    raise HTTPException(status_code=404, detail="Task not found")
            return _progress_from_state(st2)
        raise HTTPException(status_code=404, detail="Task not found")
    task_file_id = (task.get("kwargs") or {}).get("file_id") or task.get("file_id")
    if not task_file_id:
        raise HTTPException(status_code=404, detail="File not found for task")
    st2 = await state_manager.get_state(task_file_id)
    if st2:
        st_owner = st2.get("owner_id")
        if isinstance(st_owner, str) and st_owner and st_owner != owner_id:
            raise HTTPException(status_code=404, detail="Task not found")
    result2 = _progress_from_state(st2)
    # Attach DB task_type if possible
    if db_row and db_row.get("task_type"):
        tt = (db_row["task_type"] or "").lower()
        result2["task_type"] = tt
        result2["generate_video"] = tt in ("video", "both")
        result2["generate_podcast"] = tt in ("podcast", "both")
        if tt == "podcast":
            db_sub = db_row.get("subtitle_language")
            if db_sub:
                result2["subtitle_language"] = db_sub
    return result2
