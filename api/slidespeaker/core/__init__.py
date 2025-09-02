"""
Core components for SlideSpeaker
"""

# Core modules
from .task_queue import RedisTaskQueue, task_queue
from .task_manager import TaskManager, task_manager
from .state_manager import RedisStateManager, state_manager
from .pipeline import process_presentation

__all__ = [
    'RedisTaskQueue',
    'task_queue',
    'TaskManager', 
    'task_manager',
    'RedisStateManager',
    'state_manager',
    'process_presentation'
]