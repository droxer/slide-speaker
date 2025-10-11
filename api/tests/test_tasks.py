"""
Test suite for task management endpoints.
"""

from unittest.mock import AsyncMock, patch

from fastapi import Request
from fastapi.testclient import TestClient

from server import app
from slidespeaker.routes.tasks import require_authenticated_user


class TestTasksEndpoints:
    """Test cases for task management endpoints."""

    def test_get_task_status_requires_authentication(
        self, test_client: TestClient
    ) -> None:
        """Test that getting task status requires authentication."""
        response = test_client.get("/api/tasks/test-task-id/status")
        # Should require authentication
        assert response.status_code == 401

    @patch("slidespeaker.repository.task.get_task", new_callable=AsyncMock)
    @patch("slidespeaker.routes.tasks.task_queue.get_task", new_callable=AsyncMock)
    def test_get_task_status_success(
        self,
        mock_get_task: AsyncMock,
        mock_db_get_task: AsyncMock,
        test_client: TestClient,
    ) -> None:
        """Test successful retrieval of task status."""

        async def fake_auth(request: Request) -> dict[str, object]:
            return {"sub": "test-user", "user": {"id": "test-user-id"}}

        app.dependency_overrides[require_authenticated_user] = fake_auth

        # Mock task data
        mock_task_data = {
            "id": "test-task-id",
            "status": "processing",
            "progress": 50,
            "current_step": "generating_audio",
            "owner_id": "test-user-id",
        }
        mock_get_task.return_value = mock_task_data

        try:
            # Make request WITHOUT authentication header since we're mocking the auth function
            response = test_client.get("/api/tasks/test-task-id/status")
        finally:
            app.dependency_overrides.pop(require_authenticated_user, None)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-task-id"
        assert data["status"] == "processing"
        assert data["progress"] == 50
        assert data["current_step"] == "generating_audio"

        # Verify the task queue was called
        mock_get_task.assert_awaited_once_with("test-task-id")
        mock_db_get_task.assert_not_awaited()

    @patch("slidespeaker.repository.task.get_task", new_callable=AsyncMock)
    @patch("slidespeaker.routes.tasks.task_queue.get_task", new_callable=AsyncMock)
    def test_get_task_status_not_found(
        self,
        mock_get_task: AsyncMock,
        mock_db_get_task: AsyncMock,
        test_client: TestClient,
    ) -> None:
        """Test getting task status for non-existent task."""

        async def fake_auth(request: Request) -> dict[str, object]:
            return {"sub": "test-user", "user": {"id": "test-user-id"}}

        app.dependency_overrides[require_authenticated_user] = fake_auth

        # Mock task not found from both queue and DB
        mock_get_task.return_value = None
        mock_db_get_task.return_value = None

        try:
            # Make request with authentication header since we're mocking the auth function
            response = test_client.get(
                "/api/tasks/non-existent-task/status",
                headers={"Authorization": "Bearer fake-token"},
            )
        finally:
            app.dependency_overrides.pop(require_authenticated_user, None)

        assert response.status_code == 404

        # Verify the task queue was called
        mock_get_task.assert_awaited_once_with("non-existent-task")
        mock_db_get_task.assert_awaited_once_with("non-existent-task")

    @patch("slidespeaker.repository.task.get_task", new_callable=AsyncMock)
    @patch("slidespeaker.routes.tasks.task_queue.cancel_task", new_callable=AsyncMock)
    def test_cancel_task_success(
        self,
        mock_cancel_task: AsyncMock,
        mock_db_get_task: AsyncMock,
        test_client: TestClient,
    ) -> None:
        """Test successful task cancellation."""

        async def fake_auth(request: Request) -> dict[str, object]:
            return {"sub": "test-user", "user": {"id": "test-user-id"}}

        app.dependency_overrides[require_authenticated_user] = fake_auth

        # Mock successful cancellation and DB lookup
        mock_cancel_task.return_value = True
        mock_db_get_task.return_value = {
            "id": "test-task-id",
            "owner_id": "test-user-id",
        }

        try:
            # Make request with authentication header since we're mocking the auth function
            response = test_client.post(
                "/api/tasks/test-task-id/cancel",
                headers={"Authorization": "Bearer fake-token"},
            )
        finally:
            app.dependency_overrides.pop(require_authenticated_user, None)

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "cancelled" in data["message"].lower()

        # Verify the task queue cancel method was called
        mock_cancel_task.assert_awaited_once_with("test-task-id")
        mock_db_get_task.assert_awaited_once_with("test-task-id")
