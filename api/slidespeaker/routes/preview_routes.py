"""
Preview routes for serving video previews and related data.

Keeps preview responsibilities separate from download endpoints.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from slidespeaker.auth import require_authenticated_user
from slidespeaker.configs.redis_config import RedisConfig
from slidespeaker.core.task_queue import task_queue
from slidespeaker.storage.paths import output_object_key
from slidespeaker.video import VideoPreviewer

router = APIRouter(
    prefix="/api",
    tags=["preview"],
    dependencies=[Depends(require_authenticated_user)],
)

# Initialize video previewer
video_previewer = VideoPreviewer()


## Legacy file-based preview endpoint removed (use task-based instead)


async def _file_id_from_task(task_id: str) -> str:
    """Resolve a file_id from a task_id using the persisted mapping or task payload."""
    # First, try the persisted mapping
    try:
        redis = RedisConfig.get_redis_client()
        mapped = await redis.get(f"ss:task2file:{task_id}")
        if mapped:
            return str(mapped)
    except Exception:
        pass

    # Fallback to the task payload if available
    task = await task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    file_id = (task.get("kwargs") or {}).get("file_id") or task.get("file_id")
    if not file_id or not isinstance(file_id, str):
        raise HTTPException(status_code=404, detail="File not found for task")
    return str(file_id)


@router.get("/tasks/{task_id}/preview")
async def get_video_preview_by_task(
    task_id: str, language: str | None = None
) -> dict[str, Any]:
    """Task-based preview endpoint that resolves file_id internally."""
    file_id = await _file_id_from_task(task_id)
    # If no language provided, let previewer default internally
    try:
        return video_previewer.generate_preview_data(file_id, language or "english")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate preview: {str(e)}"
        ) from e


@router.options("/tasks/{task_id}/preview")
async def options_task_preview(_task_id: str) -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Max-Age": "86400",
    }


@router.head("/tasks/{task_id}/preview")
async def head_task_preview(task_id: str) -> Any:
    """Quick existence check for preview resources (video)."""
    from .download_helpers import check_file_exists

    file_id = await _file_id_from_task(task_id)
    candidate_keys = [
        output_object_key(task_id, "video", "final.mp4"),
        output_object_key(file_id, "video", "final.mp4"),
        f"{task_id}.mp4",
        f"{file_id}.mp4",
        f"{file_id}_final.mp4",
    ]
    if any(check_file_exists(k) for k in candidate_keys):
        return {}
    raise HTTPException(status_code=404, detail="Preview not available")
