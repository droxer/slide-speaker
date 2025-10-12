"""
Shared helpers for FastAPI route modules.

Provides factory functions for authenticated routers and task ownership checks so
individual route modules don't have to duplicate the same boilerplate.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from slidespeaker.auth import extract_user_id, require_authenticated_user
from slidespeaker.core.state_manager import state_manager
from slidespeaker.repository.task import get_task as db_get_task


def create_authenticated_router(tag: str, *, prefix: str = "/api") -> APIRouter:
    """
    Create a router scoped to the `/api` prefix with authentication enforced.

    Route modules can call this helper instead of repeating the prefix, tag
    declaration, and `require_authenticated_user` dependency in every file.
    """
    return APIRouter(
        prefix=prefix,
        tags=[tag],
        dependencies=[Depends(require_authenticated_user)],
    )


async def require_task_for_user(
    task_id: str,
    current_user: dict[str, Any],
    *,
    include_state: bool = False,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """
    Fetch a task row for the current user and optionally hydrate its state.

    Raises 403 when the session is missing an ID and 404 when the task does not
    belong to the current user. Returns the database row (always) and the
    in-memory state when `include_state=True`.
    """
    owner_id = extract_user_id(current_user)
    if not owner_id:
        raise HTTPException(status_code=403, detail="user session missing id")

    row = await db_get_task(task_id)
    if not row or row.get("owner_id") != owner_id:
        raise HTTPException(status_code=404, detail="Task not found")

    state: dict[str, Any] | None = None
    if include_state:
        file_id = row.get("file_id")
        if isinstance(file_id, str) and file_id:
            state = await state_manager.get_state(file_id)
        if not state:
            state = await state_manager.get_state_by_task(task_id)

        if state and isinstance(state, dict):
            st_owner = state.get("owner_id")
            if isinstance(st_owner, str) and st_owner and st_owner != owner_id:
                raise HTTPException(status_code=404, detail="Task not found")

    return row, state


__all__ = ["create_authenticated_router", "require_task_for_user"]
