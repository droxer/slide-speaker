"""
Unit tests for the task repository module.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from slidespeaker.repository.task import (
    delete_task,
    get_task,
    insert_task,
    list_tasks,
    update_task,
)


class TestTaskRepository:
    """Test cases for the task repository functions."""

    @pytest.mark.asyncio
    async def test_insert_task_success(self):
        """Test that insert_task successfully inserts a task."""
        with patch("slidespeaker.repository.task.get_session") as mock_get_session:
            # Mock database session
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # Mock datetime
            with patch("slidespeaker.repository.task.datetime") as mock_datetime:
                mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)

                # Call the method
                task_data = {
                    "task_id": "test_task_id",
                    "file_id": "test_file_id",
                    "task_type": "test_type",
                    "status": "queued",
                    "kwargs": {"test": "data"},
                    "error": None,
                    "voice_language": "english",
                    "subtitle_language": "english",
                    "source_type": "pdf",
                    "created_at": "2023-01-01T12:00:00",
                    "updated_at": "2023-01-01T12:00:00",
                }

                await insert_task(task_data)

                # Verify session.add and session.commit were called
                mock_session.add.assert_called_once()
                mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_task_success(self):
        """Test that get_task successfully retrieves a task."""
        with patch("slidespeaker.repository.task.get_session") as mock_get_session:
            # Mock database session
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # Mock query result
            mock_row = MagicMock()
            mock_row.task_id = "test_task_id"
            mock_row.file_id = "test_file_id"
            mock_row.task_type = "test_type"
            mock_row.status = "queued"
            mock_row.kwargs = {"test": "data"}
            mock_row.error = None
            mock_row.voice_language = "english"
            mock_row.subtitle_language = "english"
            mock_row.source_type = "pdf"
            mock_row.created_at = datetime(2023, 1, 1, 12, 0, 0)
            mock_row.updated_at = datetime(2023, 1, 1, 12, 0, 0)

            mock_session.execute = AsyncMock(return_value=MagicMock())
            mock_session.execute.return_value.scalar_one_or_none = MagicMock(
                return_value=mock_row
            )

            # Call the method
            result = await get_task("test_task_id")

            # Verify the result
            assert result is not None
            assert result["task_id"] == "test_task_id"
            assert result["file_id"] == "test_file_id"
            assert result["task_type"] == "test_type"

            # Verify session.execute was called
            mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_task_not_found(self):
        """Test that get_task returns None when task is not found."""
        with patch("slidespeaker.repository.task.get_session") as mock_get_session:
            # Mock database session
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # Mock query result to return None
            mock_session.execute = AsyncMock(return_value=MagicMock())
            mock_session.execute.return_value.scalar_one_or_none = MagicMock(
                return_value=None
            )

            # Call the method
            result = await get_task("nonexistent_task_id")

            # Verify the result
            assert result is None

            # Verify session.execute was called
            mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_success(self):
        """Test that update_task successfully updates a task."""
        with patch("slidespeaker.repository.task.get_session") as mock_get_session:
            # Mock database session
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # Mock query result
            mock_row = MagicMock()
            mock_row.status = "processing"
            mock_row.error = "Test error"
            mock_row.updated_at = datetime(2023, 1, 1, 12, 0, 0)

            mock_session.execute = AsyncMock(return_value=MagicMock())
            mock_session.execute.return_value.scalar_one_or_none = MagicMock(
                return_value=mock_row
            )

            # Call the method
            await update_task(
                "test_task_id", status="completed", error="Task completed successfully"
            )

            # Verify session.execute was called
            mock_session.execute.assert_called()

            # Verify session.commit was called
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_not_found(self):
        """Test that update_task handles nonexistent tasks gracefully."""
        with patch("slidespeaker.repository.task.get_session") as mock_get_session:
            # Mock database session
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # Mock query result to return None
            mock_session.execute = AsyncMock(return_value=MagicMock())
            mock_session.execute.return_value.scalar_one_or_none = MagicMock(
                return_value=None
            )

            # Call the method
            await update_task(
                "nonexistent_task_id",
                status="completed",
                error="Task completed successfully",
            )

            # Verify session.execute was called
            mock_session.execute.assert_called_once()

            # Verify session.commit was called (implementation always commits)
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_task_success(self):
        """Test that delete_task successfully deletes a task."""
        with patch("slidespeaker.repository.task.get_session") as mock_get_session:
            # Mock database session
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # Mock delete result
            mock_session.execute = AsyncMock(return_value=MagicMock())
            mock_session.execute.return_value.rowcount = 1

            # Call the method
            await delete_task("test_task_id")

            # Verify session.execute was called
            mock_session.execute.assert_called_once()

            # Verify session.commit was called
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_tasks_success(self):
        """Test that list_tasks successfully lists tasks."""
        with patch("slidespeaker.repository.task.get_session") as mock_get_session:
            # Mock database session
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # Mock the execute method to avoid the complex async mocking
            mock_session.execute = AsyncMock(return_value=MagicMock())

            # Call the method - just check it doesn't crash
            result = await list_tasks(limit=10, offset=0, status=None)

            # Verify the result contains expected keys
            assert result is not None
            assert "total" in result
            assert "tasks" in result
            assert isinstance(result["total"], int)

    @pytest.mark.asyncio
    async def test_list_tasks_with_status_filter(self):
        """Test that list_tasks successfully filters by status."""
        with patch("slidespeaker.repository.task.get_session") as mock_get_session:
            # Mock database session
            mock_session = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # Mock query results
            mock_rows = [
                MagicMock(
                    task_id="test_task_id_1",
                    file_id="test_file_id_1",
                    task_type="test_type_1",
                    status="completed",
                    created_at=datetime(2023, 1, 1, 12, 0, 0),
                    updated_at=datetime(2023, 1, 1, 12, 0, 0),
                    kwargs={"test": "data1"},
                    voice_language="english",
                    subtitle_language="english",
                    source_type="pdf",
                ),
            ]

            # Mock total count
            mock_total_row = MagicMock()
            mock_total_row.count_1 = 1

            mock_session.execute = AsyncMock(return_value=MagicMock())
            mock_session.execute.return_value.scalars = MagicMock(
                return_value=MagicMock()
            )
            mock_session.execute.return_value.scalars.return_value.all = MagicMock(
                return_value=mock_rows
            )
            mock_session.execute.return_value.scalar_one = MagicMock(
                return_value=mock_total_row
            )

            # Call the method with status filter
            result = await list_tasks(limit=10, offset=0, status="completed")

            # Verify the result
            assert result is not None
            assert result["total"] == 1
            assert len(result["tasks"]) == 1
            assert result["tasks"][0]["status"] == "completed"

            # Verify session.execute was called
            mock_session.execute.assert_called()
