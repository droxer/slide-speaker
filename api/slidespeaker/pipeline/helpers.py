"""
Shared helpers for pipeline step execution.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.core.task_queue import task_queue


async def check_and_handle_cancellation(
    file_id: str, step_key: str, task_id: str | None = None
) -> bool:
    """
    Return True when the task has been cancelled (either via queue or state), marking the
    state as cancelled for the provided step.
    """
    if task_id and await task_queue.is_task_cancelled(task_id):
        logger.info("Task %s cancelled via queue during step %s", task_id, step_key)
        await state_manager.mark_cancelled(file_id, cancelled_step=step_key)
        return True

    state = await state_manager.get_state(file_id)
    if state and state.get("status") == "cancelled":
        logger.info(
            "Task %s already marked cancelled in state; step %s will be skipped",
            task_id or file_id,
            step_key,
        )
        await state_manager.mark_cancelled(file_id, cancelled_step=step_key)
        return True
    return False


async def set_step_status_processing(
    file_id: str, step_key: str, task_id: str | None = None
) -> None:
    """Mark a step as processing in the state."""
    if task_id:
        await state_manager.update_step_status_by_task(task_id, step_key, "processing")
    else:
        await state_manager.update_step_status(file_id, step_key, "processing")


async def fetch_step_state(file_id: str, step_key: str) -> dict[str, Any] | None:
    """Retrieve a step state dictionary."""
    return await state_manager.get_step_status(file_id, step_key)
