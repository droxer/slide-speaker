"""
Admin and system-related routes.
"""

from typing import Any

from fastapi import APIRouter, Depends

from slidespeaker.auth import require_authenticated_user
from slidespeaker.core.state_manager import state_manager

router = APIRouter(
    prefix="/api",
    tags=["admin"],
    dependencies=[Depends(require_authenticated_user)],
)


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
