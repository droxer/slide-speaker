"""
Test suite for upload endpoints.
"""

from unittest.mock import AsyncMock, patch

from fastapi import Request
from fastapi.testclient import TestClient

from server import app
from slidespeaker.routes.upload_routes import require_authenticated_user


class TestUploadEndpoints:
    """Test cases for upload endpoints."""

    def test_upload_endpoint_requires_authentication(
        self, test_client: TestClient
    ) -> None:
        """Test that upload endpoint requires authentication."""
        response = test_client.post("/api/upload")
        # Should require authentication
        assert response.status_code == 401

    @patch(
        "slidespeaker.core.task_queue.task_queue.submit_task", new_callable=AsyncMock
    )
    def test_upload_valid_json_payload(
        self,
        mock_submit_task: AsyncMock,
        test_client: TestClient,
    ) -> None:
        """Test upload with valid JSON payload."""

        async def fake_auth(request: Request) -> dict[str, object]:
            return {"sub": "test-user"}

        app.dependency_overrides[require_authenticated_user] = fake_auth

        # Mock task submission
        mock_submit_task.return_value = "test-task-id"

        # Test payload
        payload = {
            "filename": "test.pdf",
            "file_data": "dGVzdCBmaWxlIGNvbnRlbnQ=",  # base64 encoded "test file content"
            "voice_language": "english",
            "video_resolution": "hd",
            "generate_avatar": True,
            "generate_subtitles": True,
            "task_type": "video",
            "source_type": "pdf",
        }

        try:
            # Make request with authentication header since we're mocking the auth function
            response = test_client.post(
                "/api/upload",
                json=payload,
                headers={"Authorization": "Bearer fake-token"},
            )
        finally:
            app.dependency_overrides.pop(require_authenticated_user, None)

        assert response.status_code == 200
        data = response.json()
        assert "file_id" in data
        assert "task_id" in data
        assert data["task_id"] == "test-task-id"
        assert "message" in data

        # Verify task was submitted
        mock_submit_task.assert_awaited_once()
