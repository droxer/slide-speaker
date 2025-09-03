"""
Core components for SlideSpeaker
"""

# Core modules
from .pipeline import process_presentation
from .state_manager import RedisStateManager, state_manager
from .task_manager import TaskManager, task_manager
from .task_queue import RedisTaskQueue, task_queue

__all__ = [
    "RedisTaskQueue",
    "task_queue",
    "TaskManager",
    "task_manager",
    "RedisStateManager",
    "state_manager",
    "process_presentation",
]
