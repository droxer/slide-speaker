"""
Task management module for SlideSpeaker.
This module provides local task management capabilities for tracking task status in memory.
Note: Most task management is handled by RedisTaskQueue, this is a legacy component.
"""

from typing import Any


class TaskManager:
    """Local task manager for tracking task status in memory"""

    def __init__(self) -> None:
        """Initialize the task manager with empty task dictionary"""
        self.tasks: dict[str, dict[str, Any]] = {}
        self.task_queue = None

    def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """Get task status by ID from local memory storage"""
        return self.tasks.get(task_id)


# Global task manager instance
task_manager = TaskManager()
