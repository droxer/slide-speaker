"""
Unit tests for the Redis task queue module.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from slidespeaker.core.task_queue import RedisTaskQueue


class TestRedisTaskQueue:
    """Test cases for the RedisTaskQueue class."""

    @pytest.fixture
    def task_queue(self):
        """Create a RedisTaskQueue instance with mocked dependencies."""
        with patch("slidespeaker.configs.redis_config.RedisConfig"):
            queue = RedisTaskQueue()
            queue.redis_client = AsyncMock()
            return queue

    @pytest.mark.asyncio
    async def test_submit_task_success(self, task_queue):
        """Test that submit_task successfully creates and queues a task."""
        # Mock UUID and datetime
        with (
            patch(
                "slidespeaker.core.task_queue.uuid.uuid4", return_value="test-task-id"
            ),
            patch("slidespeaker.core.task_queue.db_enabled", True),
            patch("slidespeaker.core.task_queue.insert_task") as mock_insert_task,
        ):
            # Mock datetime using the actual import
            mock_datetime = MagicMock()
            mock_datetime.now.return_value.isoformat.return_value = (
                "2023-01-01T00:00:00"
            )

            # Call the method
            task_id = await task_queue.submit_task(
                task_type="test_type",
                file_id="test_file_id",
                file_path="/test/path/file.pdf",
            )

            # Verify the result
            assert task_id == "test-task-id"

            # Verify Redis set was called
            task_queue.redis_client.set.assert_called_once()

            # Verify Redis rpush was called
            task_queue.redis_client.rpush.assert_called_once()

            # Verify database insert was called
            mock_insert_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_task_success(self, task_queue):
        """Test that get_task successfully retrieves a task."""
        # Mock Redis response
        mock_task_data = {
            "task_id": "test-task-id",
            "task_type": "test_type",
            "status": "queued",
            "kwargs": {"file_id": "test_file_id"},
        }
        task_queue.redis_client.get = AsyncMock(return_value=json.dumps(mock_task_data))

        # Call the method
        result = await task_queue.get_task("test-task-id")

        # Verify the result
        assert result is not None
        assert result["task_id"] == "test-task-id"
        assert result["task_type"] == "test_type"

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, task_queue):
        """Test that get_task returns None when task is not found."""
        # Mock Redis response
        task_queue.redis_client.get = AsyncMock(return_value=None)

        # Call the method
        result = await task_queue.get_task("test-task-id")

        # Verify the result
        assert result is None

    @pytest.mark.asyncio
    async def test_update_task_status_success(self, task_queue):
        """Test that update_task_status successfully updates a task's status."""
        # Mock task data
        mock_task = {
            "task_id": "test-task-id",
            "task_type": "test_type",
            "status": "queued",
            "kwargs": {"test": "data"},
            "error": None,
            "voice_language": "english",
            "subtitle_language": "english",
            "source_type": "pdf",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00",
        }

        # Mock Redis response
        task_queue.redis_client.get = AsyncMock(return_value=json.dumps(mock_task))
        task_queue.redis_client.set = AsyncMock(return_value=True)

        # Mock database enabled flag and update function
        with (
            patch("slidespeaker.core.task_queue.db_enabled", True),
            patch("slidespeaker.core.task_queue.update_task") as mock_update_task,
        ):
            # Call the method
            result = await task_queue.update_task_status("test-task-id", "processing")

            # Verify the result
            assert result is True

            # Verify Redis get was called
            task_queue.redis_client.get.assert_called_once()

            # Verify Redis set was called
            task_queue.redis_client.set.assert_called_once()

            # Verify database update was called
            mock_update_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_status_task_not_found(self, task_queue):
        """Test that update_task_status returns False when task is not found."""
        # Mock Redis response
        task_queue.redis_client.get = AsyncMock(return_value=None)

        # Call the method
        result = await task_queue.update_task_status("test-task-id", "processing")

        # Verify the result
        assert result is False

    @pytest.mark.asyncio
    async def test_get_next_task_success(self, task_queue):
        """Test that get_next_task successfully retrieves the next task."""
        # Mock Redis response
        task_queue.redis_client.brpop = AsyncMock(
            return_value=("ss:task_queue", "test-task-id")
        )

        # Call the method
        result = await task_queue.get_next_task()

        # Verify the result
        assert result == "test-task-id"

    @pytest.mark.asyncio
    async def test_get_next_task_timeout(self, task_queue):
        """Test that get_next_task returns None when no tasks are available."""
        # Mock Redis response (timeout)
        task_queue.redis_client.brpop = AsyncMock(return_value=None)

        # Call the method
        result = await task_queue.get_next_task()

        # Verify the result
        assert result is None

    @pytest.mark.asyncio
    async def test_cancel_task_queued(self, task_queue):
        """Test that cancel_task successfully cancels a queued task."""
        # Mock existing task
        mock_task = {
            "task_id": "test-task-id",
            "status": "queued",
            "kwargs": {"file_id": "test_file_id"},
        }
        task_queue.redis_client.get = AsyncMock(return_value=json.dumps(mock_task))

        # Mock Redis lrem response
        task_queue.redis_client.lrem = AsyncMock(return_value=1)

        # Call the method
        result = await task_queue.cancel_task("test-task-id")

        # Verify the result
        assert result is True

        # Verify Redis lrem was called
        task_queue.redis_client.lrem.assert_called()

        # Verify Redis set was called to update task status
        task_queue.redis_client.set.assert_called()

    @pytest.mark.asyncio
    async def test_cancel_task_processing(self, task_queue):
        """Test that cancel_task marks a processing task for cancellation."""
        # Mock existing task
        mock_task = {
            "task_id": "test-task-id",
            "status": "processing",
            "kwargs": {"file_id": "test_file_id"},
        }
        task_queue.redis_client.get = AsyncMock(return_value=json.dumps(mock_task))

        # Call the method
        result = await task_queue.cancel_task("test-task-id")

        # Verify the result
        assert result is True

        # Verify Redis set was called to update task status
        task_queue.redis_client.set.assert_called()

        # Verify Redis setex was called to set cancellation flag
        task_queue.redis_client.setex.assert_called()

    @pytest.mark.asyncio
    async def test_cancel_task_not_found(self, task_queue):
        """Test that cancel_task returns False when task is not found."""
        # Mock Redis response
        task_queue.redis_client.get = AsyncMock(return_value=None)

        # Call the method
        result = await task_queue.cancel_task("test-task-id")

        # Verify the result
        assert result is False

    @pytest.mark.asyncio
    async def test_is_task_cancelled_already_cancelled(self, task_queue):
        """Test that is_task_cancelled returns True when task is already cancelled."""
        # Mock existing task with cancelled status
        mock_task = {
            "task_id": "test-task-id",
            "status": "cancelled",
            "kwargs": {"file_id": "test_file_id"},
        }
        task_queue.redis_client.get = AsyncMock(return_value=json.dumps(mock_task))

        # Call the method
        result = await task_queue.is_task_cancelled("test-task-id")

        # Verify the result
        assert result is True

    @pytest.mark.asyncio
    async def test_is_task_cancelled_immediate_flag(self, task_queue):
        """Test that is_task_cancelled checks for immediate cancellation flag."""
        # Mock existing task with non-cancelled status
        mock_task = {
            "task_id": "test-task-id",
            "status": "processing",
            "kwargs": {"file_id": "test_file_id"},
        }
        task_queue.redis_client.get = AsyncMock(return_value=json.dumps(mock_task))

        # Mock Redis exists response for cancellation flag
        task_queue.redis_client.exists = AsyncMock(return_value=1)

        # Call the method
        result = await task_queue.is_task_cancelled("test-task-id")

        # Verify the result
        assert result is True

    @pytest.mark.asyncio
    async def test_is_task_cancelled_not_cancelled(self, task_queue):
        """Test that is_task_cancelled returns False when task is not cancelled."""
        # Mock existing task with non-cancelled status
        mock_task = {
            "task_id": "test-task-id",
            "status": "processing",
            "kwargs": {"file_id": "test_file_id"},
        }
        task_queue.redis_client.get = AsyncMock(return_value=json.dumps(mock_task))

        # Mock Redis exists response for cancellation flag
        task_queue.redis_client.exists = AsyncMock(return_value=0)

        # Call the method
        result = await task_queue.is_task_cancelled("test-task-id")

        # Verify the result
        assert result is False

    @pytest.mark.asyncio
    async def test_clear_cancellation_flag(self, task_queue):
        """clear_cancellation_flag should remove the cancellation key."""
        task_queue.redis_client.delete = AsyncMock()

        await task_queue.clear_cancellation_flag("task-123")

        task_queue.redis_client.delete.assert_called_once_with(
            "ss:task:task-123:cancelled"
        )

    @pytest.mark.asyncio
    async def test_enqueue_existing_task_success(self, task_queue):
        """enqueue_existing_task requeues eligible tasks."""
        task_queue.get_task = AsyncMock(
            return_value={
                "status": "failed",
                "error": "boom",
                "task_id": "task-123",
            }
        )
        task_queue.redis_client.lrem = AsyncMock(return_value=1)
        task_queue.redis_client.rpush = AsyncMock()
        task_queue.redis_client.set = AsyncMock()
        task_queue.clear_cancellation_flag = AsyncMock()
        with patch("slidespeaker.core.task_queue.db_enabled", False):
            result = await task_queue.enqueue_existing_task("task-123")

        assert result is True
        task_queue.redis_client.rpush.assert_called_once_with(
            task_queue.queue_key, "task-123"
        )
        task_queue.clear_cancellation_flag.assert_called_once_with("task-123")

    @pytest.mark.asyncio
    async def test_enqueue_existing_task_missing(self, task_queue):
        """enqueue_existing_task returns False when task is absent."""
        task_queue.get_task = AsyncMock(return_value=None)

        result = await task_queue.enqueue_existing_task("missing-task")

        assert result is False

    @pytest.mark.asyncio
    async def test_enqueue_existing_task_invalid_status(self, task_queue):
        """enqueue_existing_task declines tasks in unexpected statuses."""
        task_queue.get_task = AsyncMock(
            return_value={
                "status": "processing",
                "task_id": "task-123",
            }
        )

        result = await task_queue.enqueue_existing_task("task-123")

        assert result is False

    @pytest.mark.asyncio
    async def test_complete_task_processing(self, task_queue):
        """complete_task_processing should acknowledge completion."""
        result = await task_queue.complete_task_processing("task-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_get_task_status(self, task_queue):
        """get_task_status returns the stored status value."""
        task_queue.get_task = AsyncMock(
            return_value={
                "task_id": "task-123",
                "status": "queued",
            }
        )

        status = await task_queue.get_task_status("task-123")

        assert status == "queued"
