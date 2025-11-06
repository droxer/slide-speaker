import json
from unittest.mock import AsyncMock

import pytest

from scripts import task_status_cli


@pytest.mark.asyncio
async def test_fetch_tasks_filters_and_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    redis_client = AsyncMock()
    redis_client.scan = AsyncMock(return_value=(0, [b"ss:task:a", b"ss:task:b"]))
    redis_client.get = AsyncMock(
        side_effect=[
            json.dumps(
                {
                    "task_id": "a",
                    "status": "failed",
                    "created_at": "2024-02-01T10:00:00",
                }
            ),
            json.dumps(
                {
                    "task_id": "b",
                    "status": "completed",
                    "created_at": "2024-03-01T10:00:00",
                }
            ),
        ]
    )

    monkeypatch.setattr(task_status_cli.task_queue, "redis_client", redis_client)

    tasks = await task_status_cli.fetch_tasks(status="failed", limit=5)
    assert len(tasks) == 1
    assert tasks[0]["task_id"] == "a"
    redis_client.scan.assert_called_once()
    assert redis_client.get.call_count == 2


@pytest.mark.asyncio
async def test_set_task_status_updates_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    update_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(task_status_cli.task_queue, "update_task_status", update_mock)
    mark_failed = AsyncMock()
    monkeypatch.setattr(
        task_status_cli.state_manager, "mark_failed_by_task", mark_failed
    )
    monkeypatch.setattr(
        task_status_cli.state_manager, "mark_completed_by_task", AsyncMock()
    )
    monkeypatch.setattr(
        task_status_cli.state_manager, "mark_cancelled_by_task", AsyncMock()
    )
    monkeypatch.setattr(
        task_status_cli.state_manager, "set_status_by_task", AsyncMock()
    )

    success = await task_status_cli.set_task_status(
        "task-123", "failed", error="manual"
    )
    assert success is True
    update_mock.assert_awaited_once_with("task-123", "failed", error="manual")
    mark_failed.assert_awaited_once_with("task-123")


@pytest.mark.asyncio
async def test_set_task_status_invalid_status() -> None:
    with pytest.raises(ValueError):
        await task_status_cli.set_task_status("task-123", "unknown")


@pytest.mark.asyncio
async def test_set_task_status_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    update_mock = AsyncMock(return_value=False)
    monkeypatch.setattr(task_status_cli.task_queue, "update_task_status", update_mock)
    monkeypatch.setattr(
        task_status_cli.state_manager, "mark_completed_by_task", AsyncMock()
    )
    monkeypatch.setattr(
        task_status_cli.state_manager, "mark_failed_by_task", AsyncMock()
    )
    monkeypatch.setattr(
        task_status_cli.state_manager, "mark_cancelled_by_task", AsyncMock()
    )
    monkeypatch.setattr(
        task_status_cli.state_manager, "set_status_by_task", AsyncMock()
    )

    success = await task_status_cli.set_task_status("task-123", "processing")
    assert success is False
    update_mock.assert_awaited_once()
