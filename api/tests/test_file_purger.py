"""
Unit tests for the file purger module.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from slidespeaker.jobs.file_purger import FilePurger


class TestFilePurger:
    """Test cases for the FilePurger class."""

    @pytest.fixture
    def file_purger(self):
        """Create a FilePurger instance with mocked dependencies."""
        with (
            patch("slidespeaker.storage.StorageConfig"),
            patch("slidespeaker.jobs.file_purger.get_storage_provider"),
            patch("slidespeaker.jobs.file_purger.config"),
        ):
            purger = FilePurger()
            purger.storage_provider = MagicMock()
            purger.output_dir = MagicMock()
            return purger

    @pytest.mark.asyncio
    async def test_enqueue_file_purge_success(self, file_purger):
        """Test that enqueue_file_purge successfully submits a task."""
        # Mock the task queue
        with patch("slidespeaker.jobs.file_purger.task_queue") as mock_task_queue:
            mock_task_queue.submit_task = AsyncMock(return_value="test_task_id")

            # Call the method
            result = await file_purger.enqueue_file_purge("test_file_id")

            # Verify the result
            assert result == "test_task_id"
            mock_task_queue.submit_task.assert_called_once_with(
                task_type="file_purge", file_id="test_file_id"
            )

    @pytest.mark.asyncio
    async def test_enqueue_file_purge_failure(self, file_purger):
        """Test that enqueue_file_purge handles submission failures gracefully."""
        # Mock the task queue to raise an exception
        with patch("slidespeaker.jobs.file_purger.task_queue") as mock_task_queue:
            mock_task_queue.submit_task = AsyncMock(side_effect=Exception("Test error"))

            # Call the method
            result = await file_purger.enqueue_file_purge("test_file_id")

            # Verify the result
            assert result is None

    @pytest.mark.asyncio
    async def test_purge_task_files_local_storage_success(self, file_purger):
        """Test that purge_task_files successfully purges files in local storage."""
        # Mock state manager to return a valid state
        mock_state = {"file_path": "/test/path/file.pdf"}

        with (
            patch("slidespeaker.jobs.file_purger.state_manager") as mock_state_manager,
            patch("slidespeaker.jobs.file_purger.config") as mock_config,
            patch("slidespeaker.jobs.file_purger.shutil") as mock_shutil,
        ):
            mock_state_manager.get_state = AsyncMock(return_value=mock_state)
            mock_config.storage_provider = "local"
            file_purger.output_dir = MagicMock()

            # Call the method
            await file_purger.purge_task_files("test_file_id")

            # Verify shutil.rmtree was called
            mock_shutil.rmtree.assert_called_once()

    @pytest.mark.asyncio
    async def test_purge_task_files_no_state(self, file_purger):
        """Test that purge_task_files handles missing state gracefully."""
        # Mock state manager to return None
        with patch("slidespeaker.jobs.file_purger.state_manager") as mock_state_manager:
            mock_state_manager.get_state = AsyncMock(return_value=None)

            # Call the method (should not raise an exception)
            await file_purger.purge_task_files("test_file_id")

    @pytest.mark.asyncio
    async def test_purge_task_files_no_file_path(self, file_purger):
        """Test that purge_task_files handles missing file_path gracefully."""
        # Mock state manager to return state without file_path
        mock_state = {}

        with patch("slidespeaker.jobs.file_purger.state_manager") as mock_state_manager:
            mock_state_manager.get_state = AsyncMock(return_value=mock_state)

            # Call the method (should not raise an exception)
            await file_purger.purge_task_files("test_file_id")
