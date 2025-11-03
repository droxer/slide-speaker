"""
Test suite for health check endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test cases for health check endpoints."""

    def test_health_endpoint_success(self, test_client: TestClient) -> None:
        """Test successful health check."""
        with (
            patch(
                "slidespeaker.routes.health_routes.RedisConfig.get_redis_client"
            ) as mock_redis,
            patch("slidespeaker.configs.db.get_session") as mock_db,
        ):
            # Mock Redis ping to return True (success)
            mock_redis_client = AsyncMock()
            mock_redis_client.ping = AsyncMock(return_value=True)
            mock_redis.return_value = mock_redis_client

            # Mock database connection
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(return_value=MagicMock())
            mock_db.return_value.__aenter__.return_value = mock_session

            response = test_client.get("/api/health")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] in ["ok", "degraded"]
            assert "redis" in data
            assert "db" in data

    def test_health_endpoint_redis_failure(self, test_client: TestClient) -> None:
        """Test health check when Redis is unavailable."""
        with (
            patch(
                "slidespeaker.routes.health_routes.RedisConfig.get_redis_client"
            ) as mock_redis,
            patch("slidespeaker.configs.db.get_session") as mock_db,
        ):
            # Mock Redis ping to raise an exception (failure)
            mock_redis.side_effect = Exception("Redis connection failed")

            # Mock database connection
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(return_value=MagicMock())
            mock_db.return_value.__aenter__.return_value = mock_session

            response = test_client.get("/api/health")
            assert (
                response.status_code == 200
            )  # Still returns 200 but with degraded status

            data = response.json()
            assert data["status"] in ["degraded", "down"]
            assert "redis" in data
            assert "db" in data

    def test_health_endpoint_db_failure(self, test_client: TestClient) -> None:
        """Test health check when database is unavailable."""
        with (
            patch(
                "slidespeaker.routes.health_routes.RedisConfig.get_redis_client"
            ) as mock_redis,
            patch("slidespeaker.configs.db.get_session") as mock_db,
        ):
            # Mock successful Redis ping
            mock_redis_client = AsyncMock()
            mock_redis_client.ping = AsyncMock(return_value=True)
            mock_redis.return_value = mock_redis_client

            # Mock database connection failure
            mock_db.side_effect = Exception("Database connection failed")

            response = test_client.get("/api/health")
            assert (
                response.status_code == 200
            )  # Still returns 200 but with degraded status

            data = response.json()
            assert data["status"] in ["degraded", "down"]
            assert "redis" in data
            assert "db" in data
