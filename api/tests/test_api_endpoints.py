"""
Test suite for SlideSpeaker API endpoints.
"""

import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from server import app


class TestAPIServer(unittest.TestCase):
    """Test cases for the main API server."""

    def setUp(self) -> None:
        """Set up test client before each test."""
        self.client = TestClient(app)

    def test_root_endpoint(self) -> None:
        """Test that the root endpoint returns the expected welcome message."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
        self.assertEqual(data["message"], "SlideSpeaker Backend API")


class TestHealthEndpoints(unittest.TestCase):
    """Test cases for health check endpoints."""

    def setUp(self) -> None:
        """Set up test client before each test."""
        self.client = TestClient(app)

    @patch("slidespeaker.routes.health_routes.RedisConfig.get_redis_client")
    @patch("slidespeaker.configs.db.get_session")
    def test_health_endpoint(
        self, mock_get_session: MagicMock, mock_get_redis_client: MagicMock
    ) -> None:
        """Test the health endpoint."""
        # Mock successful Redis ping
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_get_redis_client.return_value = mock_redis

        # Mock successful database connection
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock())
        mock_get_session.return_value.__aenter__.return_value = mock_session

        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("redis", data)
        self.assertIn("db", data)


class TestAuthEndpoints(unittest.TestCase):
    """Test cases for authentication endpoints."""

    def setUp(self) -> None:
        """Set up test client before each test."""
        self.client = TestClient(app)

    @patch(
        "slidespeaker.routes.auth_routes.verify_user_credentials",
        new_callable=AsyncMock,
    )
    def test_login_endpoint_invalid_credentials(
        self, mock_verify_user: AsyncMock
    ) -> None:
        """Test login endpoint with invalid credentials."""
        mock_verify_user.return_value = None

        response = self.client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )
        self.assertEqual(response.status_code, 401)


class TestUploadEndpoints(unittest.TestCase):
    """Test cases for upload endpoints."""

    def setUp(self) -> None:
        """Set up test client and mock data before each test."""
        self.client = TestClient(app)
        self.test_file_content = b"This is a test file content for upload testing."

    def create_test_file(self) -> str:
        """Create a temporary test file and return its path."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
            temp_file.write(self.test_file_content)
            temp_file.flush()
            return temp_file.name

    def tearDown(self) -> None:
        """Clean up after each test."""
        # Clean up any temporary files if needed
        pass


if __name__ == "__main__":
    unittest.main()
