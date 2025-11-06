"""
Unit tests for the legacy in-memory task manager.
"""

from slidespeaker.core.task_manager import TaskManager, task_manager


def test_get_task_status_returns_existing_task():
    """TaskManager returns stored task metadata."""
    manager = TaskManager()
    manager.tasks["abc123"] = {"status": "processing"}

    result = manager.get_task_status("abc123")

    assert result == {"status": "processing"}


def test_get_task_status_missing_returns_none():
    """TaskManager returns None when a task is unknown."""
    manager = TaskManager()

    result = manager.get_task_status("missing")

    assert result is None


def test_global_task_manager_instance_is_shared():
    """Global task_manager singleton can store and retrieve task data."""
    task_manager.tasks.clear()
    task_manager.tasks["shared-task"] = {"status": "queued"}

    assert task_manager.get_task_status("shared-task") == {"status": "queued"}
