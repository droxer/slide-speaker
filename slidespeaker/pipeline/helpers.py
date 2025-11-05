"""
Shared helpers for pipeline step execution.
"""

from __future__ import annotations

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.core.task_queue import task_queue
from slidespeaker.core.task_state import StepSnapshot, TaskState


async def check_and_handle_failure(
    file_id: str, step_key: str, task_id: str | None = None
) -> bool:
    """
    Return True when the overall task has already failed, preventing further processing
    and ensuring the failure state is maintained.
    """
    task_state = await state_manager.get_task_state(file_id)
    if task_state and task_state.status == "failed":
        logger.error(
            "Task %s already marked as failed; step %s will not execute",
            task_id or file_id,
            step_key,
        )
        # Ensure the step is marked as failed too
        if task_id:
            await state_manager.update_step_status_by_task(task_id, step_key, "failed")
        else:
            await state_manager.update_step_status(file_id, step_key, "failed")
        return True
    return False


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

    task_state = await state_manager.get_task_state(file_id)
    if task_state and task_state.status == "cancelled":
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


async def fetch_step_state(file_id: str, step_key: str) -> StepSnapshot | None:
    """Retrieve a structured snapshot for the requested step."""
    task_state = await state_manager.get_task_state(file_id)
    if not task_state:
        return None
    return task_state.get_step(step_key)


async def fetch_task_state(file_id: str) -> TaskState | None:
    """Convenience helper for loading structured task state."""
    return await state_manager.get_task_state(file_id)
