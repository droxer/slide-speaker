"""
Progress tracking routes for monitoring processing status.

This module provides API endpoints for retrieving detailed progress information
about presentation processing tasks, including current step, status, and errors.
"""

from typing import Any

from fastapi import APIRouter

from slidespeaker.core.state_manager import state_manager

router = APIRouter(prefix="/api", tags=["progress"])


@router.get("/progress/{file_id}")
async def get_progress(file_id: str) -> dict[str, Any]:
    """Get detailed progress information including current step and status."""
    state = await state_manager.get_state(file_id)

    if not state:
        return {
            "status": "not_found",
            "message": "File not found or processing not started",
            "progress": 0,
            "current_step": "unknown",
            "steps": {},
        }

    # Calculate overall progress percentage
    # Total steps can vary based on whether subtitle steps are included
    total_steps = len(
        [step for step in state["steps"].values() if step["status"] != "skipped"]
    )
    completed_steps = sum(
        1 for step in state["steps"].values() if step["status"] == "completed"
    )
    progress_percentage = (
        int((completed_steps / total_steps) * 100) if total_steps > 0 else 0
    )

    return {
        "status": state["status"],
        "progress": progress_percentage,
        "current_step": state["current_step"],
        "steps": state["steps"],
        "errors": state["errors"],
        "voice_language": state["voice_language"],
        "subtitle_language": state.get("subtitle_language", state["voice_language"]),
        "created_at": state["created_at"],
        "updated_at": state["updated_at"],
    }
