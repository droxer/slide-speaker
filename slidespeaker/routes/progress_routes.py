"""
Progress tracking routes for monitoring processing status.

This module provides API endpoints for retrieving detailed progress information
about presentation processing tasks, including current step, status, and errors.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from slidespeaker.auth import extract_user_id, require_authenticated_user
from slidespeaker.core.progress_utils import compute_step_percentage
from slidespeaker.core.state_manager import state_manager
from slidespeaker.core.task_state import DEFAULT_STEP_ORDER, TaskState

router = APIRouter(
    prefix="/api",
    tags=["progress"],
    dependencies=[Depends(require_authenticated_user)],
)


# Note: file-id progress route fully removed. Use /api/tasks/{task_id}/progress.


COMPACT_DROP_KEYS = {"task_config", "task_kwargs", "settings"}


def _progress_from_state(state: dict[str, Any] | None) -> dict[str, Any]:
    if not state:
        return {
            "status": "not_found",
            "message": "Task not found or processing not started",
            "progress": 0,
            "current_step": "unknown",
            "steps": {},
        }
    task_state = TaskState.from_mapping(state)
    progress_percentage = compute_step_percentage(task_state)
    ordered_steps = task_state.ordered_steps(
        DEFAULT_STEP_ORDER, normalize_status_flag=True
    )

    # Ensure podcast steps are properly included for podcast tasks
    task_type = (
        (state.get("task_type") or "").lower() if isinstance(state, dict) else ""
    )
    is_podcast_task = task_type in ("podcast", "both")

    # If this is a podcast task, make sure all steps are included in the response
    if is_podcast_task and state and isinstance(state.get("steps"), dict):
        # Add any missing steps that might not be in the ordered output
        for step_name, step_data in state["steps"].items():
            if step_name not in ordered_steps and isinstance(step_data, dict):
                ordered_steps[step_name] = {
                    "status": step_data.get("status", "pending"),
                    "data": step_data.get("data"),
                }

    errors_payload = [entry.as_dict() for entry in task_state.errors]

    return {
        "status": task_state.status or "unknown",
        "progress": progress_percentage,
        "current_step": task_state.current_step or "unknown",
        "steps": ordered_steps,
        "errors": errors_payload,
        "filename": task_state.filename,
        "file_ext": task_state.file_ext,
        "source_type": task_state.source_type,
        "voice_language": task_state.voice_language,
        "subtitle_language": task_state.effective_subtitle_language,
        "generate_podcast": task_state.generate_podcast,
        "generate_video": task_state.generate_video,
        "created_at": task_state.created_at,
        "updated_at": task_state.updated_at,
        "voice_id": task_state.voice_id,
        "podcast_host_voice": task_state.podcast_host_voice,
        "podcast_guest_voice": task_state.podcast_guest_voice,
        "task_config": task_state.task_config,
        "task_kwargs": task_state.task_kwargs,
        "settings": task_state.settings,
    }


def _apply_progress_view(payload: dict[str, Any], view: str | None) -> dict[str, Any]:
    if view != "compact":
        return payload

    compact = {
        key: value for key, value in payload.items() if key not in COMPACT_DROP_KEYS
    }

    steps = compact.get("steps")
    if isinstance(steps, dict):
        sanitized_steps: dict[str, dict[str, Any]] = {}
        for step_name, step_data in steps.items():
            if isinstance(step_data, dict):
                sanitized_steps[step_name] = {
                    key: step_data.get(key)
                    for key in ("status", "blockedByFailure")
                    if step_data.get(key) is not None
                }
            else:
                sanitized_steps[step_name] = {}
        compact["steps"] = sanitized_steps

    errors = compact.get("errors")
    if isinstance(errors, list):
        sanitized_errors: list[dict[str, Any]] = []
        for entry in errors:
            if isinstance(entry, dict):
                sanitized_errors.append(
                    {
                        key: entry.get(key)
                        for key in ("step", "error", "message", "timestamp", "code")
                        if entry.get(key) is not None
                    }
                )
        compact["errors"] = sanitized_errors

    return compact


@router.get("/tasks/{task_id}/progress")
async def get_progress_by_task(
    task_id: str,
    current_user: Annotated[dict[str, Any], Depends(require_authenticated_user)],
    view: Annotated[str | None, Query(pattern="^(compact)$")] = None,
) -> dict[str, Any]:
    """Task-based progress endpoint resolving state by task-id (task-first)."""
    from slidespeaker.core.task_queue import task_queue
    from slidespeaker.repository.task import get_task as db_get_task

    user_id = extract_user_id(current_user)
    if not user_id:
        raise HTTPException(status_code=403, detail="user session missing id")

    db_row = await db_get_task(task_id)
    if not db_row or db_row.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Task not found")

    # Prefer task-based state alias
    st = await state_manager.get_state_by_task(task_id)
    if not isinstance(st, dict):
        st = None
    if st is None and db_row and db_row.get("file_id"):
        st = await state_manager.get_state(str(db_row["file_id"]))
    if st and isinstance(st, dict):
        st_owner = st.get("user_id")
        if isinstance(st_owner, str) and st_owner and st_owner != user_id:
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
        return _apply_progress_view(result, view)

    # Fallback to task queue mapping -> file_id -> state
    task = await task_queue.get_task(task_id)
    if not task:
        # Support state-only ids (state_{file_id})
        if task_id.startswith("state_"):
            file_id = task_id.replace("state_", "")
            st2 = await state_manager.get_state(file_id)
            if st2:
                st_owner = st2.get("user_id")
                if isinstance(st_owner, str) and st_owner and st_owner != user_id:
                    raise HTTPException(status_code=404, detail="Task not found")
            return _apply_progress_view(_progress_from_state(st2), view)
        raise HTTPException(status_code=404, detail="Task not found")
    task_file_id = (task.get("kwargs") or {}).get("file_id") or task.get("file_id")
    if not task_file_id:
        raise HTTPException(status_code=404, detail="File not found for task")
    st2 = await state_manager.get_state(task_file_id)
    if st2:
        st_owner = st2.get("user_id")
        if isinstance(st_owner, str) and st_owner and st_owner != user_id:
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
    return _apply_progress_view(result2, view)
