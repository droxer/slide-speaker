"""
Base pipeline coordinator for SlideSpeaker processing.

This module provides common functionality for all pipeline types (PDF, Slides, Podcast).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.core.task_queue import task_queue

from .helpers import (
    check_and_handle_cancellation,
    check_and_handle_failure,
    fetch_step_state,
    set_step_status_processing,
)


class PipelineStepFailedError(RuntimeError):
    """Raised when a pipeline step transitions to a failed status without bubbling an exception."""


class PipelineCancelledError(RuntimeError):
    """Raised when a pipeline step reports a cancelled status."""


class BasePipeline(ABC):
    """Abstract base class for all pipelines."""

    def __init__(self, file_id: str, file_path: Path, task_id: str | None = None):
        self.file_id = file_id
        self.file_path = file_path
        self.task_id = task_id

    async def _check_and_handle_prerequisites(self) -> bool:
        """Check cancellation and failure prerequisites before executing a step."""
        if self.task_id and await task_queue.is_task_cancelled(self.task_id):
            logger.info(f"Task {self.task_id} was cancelled before processing started")
            await state_manager.mark_cancelled(self.file_id)
            return False

        # Check for failure state before proceeding with any step
        if await check_and_handle_failure(self.file_id, "initial_check", self.task_id):
            logger.error("Pipeline already failed before processing started, exiting")
            return False
        return not await check_and_handle_cancellation(
            self.file_id, "initial_check", self.task_id
        )

    async def _execute_step(self, step_name: str, step_func, *args) -> bool:
        """Execute a single pipeline step with proper status management."""
        # Check for failure/cancellation before each step
        if await check_and_handle_failure(self.file_id, step_name, self.task_id):
            logger.error(f"Pipeline already failed before step {step_name}, exiting")
            return False
        if await check_and_handle_cancellation(self.file_id, step_name, self.task_id):
            return False

        # Check if step is already completed using the structured StepSnapshot
        step_state = await fetch_step_state(self.file_id, step_name)
        if step_state and step_state.status == "completed":
            logger.info(f"Skipping already completed step: {step_name}")
            return True

        # Mark step as processing and execute
        await set_step_status_processing(self.file_id, step_name, self.task_id)
        logger.info(
            f"=== Task {self.task_id} - Executing: {self.get_step_display_name(step_name)} ==="
        )

        try:
            await step_func(*args)
            await self._finalize_step_status(step_name)
            return True
        except PipelineCancelledError as cancelled_exc:
            logger.info(str(cancelled_exc))
            return False
        except Exception as e:
            logger.error(f"Step {step_name} failed: {str(e)}")
            # Use the structured approach to update step status
            await state_manager.update_step_status(self.file_id, step_name, "failed")
            await state_manager.add_error(self.file_id, str(e), step_name)
            await state_manager.mark_failed(self.file_id)
            raise

    async def _finalize_step_status(self, state_key: str) -> None:
        """Ensure a step finished cleanly, flagging failures for upstream handling."""
        step_state = await fetch_step_state(self.file_id, state_key)
        status = step_state.get("status") if step_state else None

        if status == "failed":
            detail = ""
            data = step_state.data if step_state else None
            if isinstance(data, dict) and data.get("error"):
                detail = f": {data['error']}"
            raise PipelineStepFailedError(
                f"Step '{state_key}' failed for file {self.file_id}{detail}"
            )

        if status == "cancelled":
            raise PipelineCancelledError(
                f"Step '{state_key}' cancelled for file {self.file_id}"
            )

        if status == "completed":
            return

        # If the step neither completed nor reported failure, mark it as completed now.
        if self.task_id:
            await state_manager.update_step_status_by_task(
                self.task_id, state_key, "completed"
            )
        else:
            await state_manager.update_step_status(self.file_id, state_key, "completed")

    @abstractmethod
    def get_step_display_name(self, step_name: str) -> str:
        """Get the display name for a step."""
        pass

    @abstractmethod
    async def execute_pipeline(self) -> None:
        """Execute the full pipeline."""
        pass
