from typing import Any


class TaskManager:
    def __init__(self) -> None:
        self.tasks: dict[str, dict[str, Any]] = {}
        self.task_queue = None

    def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """Get task status by ID"""
        return self.tasks.get(task_id)


# Global task manager instance
task_manager = TaskManager()
