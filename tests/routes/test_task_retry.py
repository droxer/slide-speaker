from unittest.mock import AsyncMock, MagicMock

import pytest

from slidespeaker.routes import task_routes
from slidespeaker.routes.task_routes import TaskRetryRequest


@pytest.mark.asyncio
async def test_retry_task_endpoint_uses_current_step(monkeypatch):
    task_id = "task-123"
    user_id = "user-1"
    row = {"user_id": user_id, "file_id": "file-1"}

    monkeypatch.setattr(task_routes.limiter, "enabled", False)
    monkeypatch.setattr(task_routes, "db_get_task", AsyncMock(return_value=row))

    state = {
        "status": "failed",
        "steps": {
            "extract_slides": {"status": "pending"},
            "generate_audio": {"status": "pending"},
        },
        "current_step": "generate_audio",
        "errors": [],
    }

    monkeypatch.setattr(
        task_routes.state_manager,
        "get_state_by_task",
        AsyncMock(return_value=state),
    )
    monkeypatch.setattr(
        task_routes.state_manager,
        "reset_steps_from_task",
        AsyncMock(return_value={"status": "processing"}),
    )
    monkeypatch.setattr(
        task_routes.state_manager,
        "get_state",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(task_routes.state_manager, "bind_task", AsyncMock())
    monkeypatch.setattr(
        task_routes.task_queue,
        "enqueue_existing_task",
        AsyncMock(return_value=True),
    )

    result = await task_routes.retry_task_endpoint(
        MagicMock(),
        task_id,
        TaskRetryRequest(),
        {"user": {"id": user_id}},
    )

    assert result["step"] == "generate_audio"
    task_routes.state_manager.reset_steps_from_task.assert_awaited_once_with(
        task_id, "generate_audio"
    )
    task_routes.task_queue.enqueue_existing_task.assert_awaited_once_with(task_id)


@pytest.mark.asyncio
async def test_retry_task_endpoint_uses_first_step_when_missing_details(monkeypatch):
    task_id = "task-456"
    user_id = "user-2"
    row = {"user_id": user_id, "file_id": "file-2"}

    monkeypatch.setattr(task_routes.limiter, "enabled", False)
    monkeypatch.setattr(task_routes, "db_get_task", AsyncMock(return_value=row))

    state = {
        "status": "failed",
        "steps": {
            "extract_slides": {"status": "pending"},
            "generate_audio": {"status": "pending"},
        },
        "current_step": "unknown-step",
        "errors": [],
    }

    monkeypatch.setattr(
        task_routes.state_manager,
        "get_state_by_task",
        AsyncMock(return_value=state),
    )
    monkeypatch.setattr(
        task_routes.state_manager,
        "reset_steps_from_task",
        AsyncMock(return_value={"status": "processing"}),
    )
    monkeypatch.setattr(
        task_routes.state_manager,
        "get_state",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(task_routes.state_manager, "bind_task", AsyncMock())
    monkeypatch.setattr(
        task_routes.task_queue,
        "enqueue_existing_task",
        AsyncMock(return_value=True),
    )

    result = await task_routes.retry_task_endpoint(
        MagicMock(),
        task_id,
        TaskRetryRequest(),
        {"user": {"id": user_id}},
    )

    assert result["step"] == "extract_slides"
    task_routes.state_manager.reset_steps_from_task.assert_awaited_once_with(
        task_id, "extract_slides"
    )


@pytest.mark.asyncio
async def test_retry_task_endpoint_falls_back_to_file_state(monkeypatch):
    task_id = "task-789"
    user_id = "user-3"
    row = {"user_id": user_id, "file_id": "file-3"}

    monkeypatch.setattr(task_routes.limiter, "enabled", False)
    monkeypatch.setattr(task_routes, "db_get_task", AsyncMock(return_value=row))

    monkeypatch.setattr(
        task_routes.state_manager,
        "get_state_by_task",
        AsyncMock(return_value=None),
    )

    file_state = {
        "status": "failed",
        "steps": {
            "extract_slides": {"status": "pending"},
        },
        "current_step": "extract_slides",
        "errors": [],
    }

    bind_mock = AsyncMock()

    monkeypatch.setattr(
        task_routes.state_manager, "get_state", AsyncMock(return_value=file_state)
    )
    monkeypatch.setattr(task_routes.state_manager, "bind_task", bind_mock)
    monkeypatch.setattr(
        task_routes.state_manager,
        "reset_steps_from_task",
        AsyncMock(return_value={"status": "processing"}),
    )
    monkeypatch.setattr(
        task_routes.task_queue,
        "enqueue_existing_task",
        AsyncMock(return_value=True),
    )

    result = await task_routes.retry_task_endpoint(
        MagicMock(),
        task_id,
        TaskRetryRequest(),
        {"user": {"id": user_id}},
    )

    assert result["step"] == "extract_slides"
    bind_mock.assert_awaited_once_with("file-3", task_id)
