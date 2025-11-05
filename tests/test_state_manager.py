"""
Unit tests for the state manager module.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from slidespeaker.core.state_manager import RedisStateManager


class TestRedisStateManager:
    """Test cases for the RedisStateManager class."""

    @pytest.fixture
    def state_manager(self):
        """Create a RedisStateManager instance with mocked dependencies."""
        with patch("slidespeaker.configs.redis_config.RedisConfig"):
            manager = RedisStateManager()
            manager.redis_client = AsyncMock()
            return manager

    @pytest.mark.asyncio
    async def test_create_state_success(self, state_manager):
        """Test that create_state successfully creates initial state."""
        # Mock datetime
        with patch("slidespeaker.core.state_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = (
                "2023-01-01T00:00:00"
            )

            # Mock Redis responses
            state_manager.redis_client.set = AsyncMock()
            state_manager.redis_client.sadd = AsyncMock()
            state_manager.redis_client.expire = AsyncMock()
            state_manager.redis_client.get = AsyncMock(return_value=None)
            state_manager.redis_client.delete = AsyncMock()

            # Call the method
            result = await state_manager.create_state(
                "test_file_id",
                MagicMock(),  # file_path
                ".pdf",  # file_ext
                "test.pdf",  # filename
                "english",  # voice_language
                "english",  # subtitle_language
                None,  # transcript_language
                "hd",  # video_resolution
                True,  # generate_avatar
                True,  # generate_subtitles
                True,  # generate_video
                False,  # generate_podcast
                None,  # voice_id
                None,  # podcast_host_voice
                None,  # podcast_guest_voice
                None,  # task_kwargs
                "test_task_id",  # task_id
            )

            # Verify the result
            assert result is not None
            assert result["file_id"] == "test_file_id"
            assert result["task_id"] == "test_task_id"
            assert "task_kwargs" in result and isinstance(result["task_kwargs"], dict)
            assert result["task_kwargs"].get("voice_language") == "english"
            assert "task_config" in result and isinstance(result["task_config"], dict)
            assert "voice_id" not in result

            # Verify Redis set was called
            state_manager.redis_client.set.assert_called()

    @pytest.mark.asyncio
    async def test_get_state_success(self, state_manager):
        """Test that get_state successfully retrieves state."""
        # Mock Redis response
        mock_state = {
            "file_id": "test_file_id",
            "task_id": "test_task_id",
            "status": "processing",
        }
        state_manager.redis_client.get = AsyncMock(return_value=json.dumps(mock_state))

        # Call the method
        result = await state_manager.get_state("test_file_id")

        # Verify the result
        assert result is not None
        assert result["file_id"] == "test_file_id"
        assert result["task_id"] == "test_task_id"

    @pytest.mark.asyncio
    async def test_get_state_not_found(self, state_manager):
        """Test that get_state returns None when state is not found."""
        # Mock Redis response
        state_manager.redis_client.get = AsyncMock(return_value=None)

        # Call the method
        result = await state_manager.get_state("test_file_id")

        # Verify the result
        assert result is None

    @pytest.mark.asyncio
    async def test_update_step_status_success(self, state_manager):
        """Test that update_step_status successfully updates a step."""
        # Mock existing state
        mock_state = {
            "file_id": "test_file_id",
            "steps": {"test_step": {"status": "pending", "data": None}},
        }
        state_manager.redis_client.get = AsyncMock(return_value=json.dumps(mock_state))
        state_manager.redis_client.set = AsyncMock()

        # Call the method
        await state_manager.update_step_status(
            "test_file_id", "test_step", "completed", "test_data"
        )

        # Verify Redis set was called
        state_manager.redis_client.set.assert_called()

    @pytest.mark.asyncio
    async def test_update_step_status_state_not_found(self, state_manager):
        """Test that update_step_status handles missing state gracefully."""
        # Mock Redis response
        state_manager.redis_client.get = AsyncMock(return_value=None)
        state_manager.redis_client.set = AsyncMock()

        # Call the method (should not raise an exception)
        await state_manager.update_step_status("test_file_id", "test_step", "completed")

    @pytest.mark.asyncio
    async def test_update_step_status_step_not_found(self, state_manager):
        """Test that update_step_status handles missing step gracefully."""
        # Mock existing state without the target step
        mock_state = {
            "file_id": "test_file_id",
            "steps": {"other_step": {"status": "pending", "data": None}},
        }
        state_manager.redis_client.get = AsyncMock(return_value=json.dumps(mock_state))
        state_manager.redis_client.set = AsyncMock()

        # Call the method (should not raise an exception)
        await state_manager.update_step_status("test_file_id", "test_step", "completed")

    @pytest.mark.asyncio
    async def test_mark_completed_success(self, state_manager):
        """Test that mark_completed successfully marks state as completed."""
        # Mock existing state
        mock_state = {"file_id": "test_file_id", "status": "processing"}
        state_manager.redis_client.get = AsyncMock(return_value=json.dumps(mock_state))
        state_manager.redis_client.set = AsyncMock()

        # Call the method
        await state_manager.mark_completed("test_file_id")

        # Verify Redis set was called
        state_manager.redis_client.set.assert_called()

    @pytest.mark.asyncio
    async def test_mark_failed_success(self, state_manager):
        """Test that mark_failed successfully marks state as failed."""
        # Mock existing state
        mock_state = {"file_id": "test_file_id", "status": "processing"}
        state_manager.redis_client.get = AsyncMock(return_value=json.dumps(mock_state))
        state_manager.redis_client.set = AsyncMock()

        # Call the method
        await state_manager.mark_failed("test_file_id")

        # Verify Redis set was called
        state_manager.redis_client.set.assert_called()

    @pytest.mark.asyncio
    async def test_mark_cancelled_success(self, state_manager):
        """Test that mark_cancelled successfully marks state as cancelled."""
        # Mock existing state
        mock_state = {
            "file_id": "test_file_id",
            "status": "processing",
            "steps": {
                "step1": {"status": "processing"},
                "step2": {"status": "pending"},
            },
        }
        state_manager.redis_client.get = AsyncMock(return_value=json.dumps(mock_state))
        state_manager.redis_client.set = AsyncMock()

        # Call the method
        await state_manager.mark_cancelled("test_file_id")

        # Verify Redis set was called
        state_manager.redis_client.set.assert_called()

    @pytest.mark.asyncio
    async def test_bind_task_success(self, state_manager):
        """Test that bind_task successfully binds task to file."""
        # Mock Redis responses
        state_manager.redis_client.set = AsyncMock()
        state_manager.redis_client.sadd = AsyncMock()
        state_manager.redis_client.expire = AsyncMock()
        state_manager.redis_client.get = AsyncMock(
            return_value=json.dumps({"file_id": "test_file_id"})
        )

        # Call the method
        await state_manager.bind_task("test_file_id", "test_task_id")

        # Verify Redis set was called for task2file mapping
        state_manager.redis_client.set.assert_any_call(
            "ss:task2file:test_task_id", "test_file_id", ex=2592000
        )

        # Verify Redis set was called for file2task mapping
        state_manager.redis_client.set.assert_any_call(
            "ss:file2task:test_file_id", "test_task_id", ex=2592000
        )

    @pytest.mark.asyncio
    async def test_unbind_task_success(self, state_manager):
        """Test that unbind_task successfully unbinds task from file."""
        # Mock Redis responses
        state_manager.redis_client.srem = AsyncMock()
        state_manager.redis_client.scard = AsyncMock(return_value=5)

        # Call the method
        result = await state_manager.unbind_task("test_file_id", "test_task_id")

        # Verify the result
        assert result == 5

        # Verify Redis srem was called
        state_manager.redis_client.srem.assert_called_with(
            "ss:file2tasks:test_file_id", "test_task_id"
        )

    @pytest.mark.asyncio
    async def test_get_step_status_success(self, state_manager):
        """Test that get_step_status successfully retrieves step status."""
        # Mock existing state
        mock_state = {
            "file_id": "test_file_id",
            "steps": {"test_step": {"status": "completed", "data": "test_data"}},
        }
        state_manager.redis_client.get = AsyncMock(return_value=json.dumps(mock_state))

        # Call the method
        result = await state_manager.get_step_status("test_file_id", "test_step")

        # Verify the result
        assert result is not None
        assert result["status"] == "completed"
        assert result["data"] == "test_data"

    @pytest.mark.asyncio
    async def test_get_step_status_step_not_found(self, state_manager):
        """Test that get_step_status returns None when step is not found."""
        # Mock existing state without the target step
        mock_state = {
            "file_id": "test_file_id",
            "steps": {"other_step": {"status": "pending", "data": None}},
        }
        state_manager.redis_client.get = AsyncMock(return_value=json.dumps(mock_state))

        # Call the method
        result = await state_manager.get_step_status("test_file_id", "test_step")

        # Verify the result
        assert result is None
