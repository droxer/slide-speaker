"""
Unit tests for the health routes module.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from slidespeaker.routes.health_routes import router


class TestHealthRoutes:
    """Test cases for the health routes."""

    @pytest.fixture
    def client(self):
        """Create a TestClient for testing the health routes."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_health_endpoint_success(self, client):
        """Test that the health endpoint returns success when all services are up."""
        with (
            patch("slidespeaker.routes.health_routes.RedisConfig") as mock_redis_config,
            patch("slidespeaker.routes.health_routes.get_session") as mock_get_session,
        ):
            # Mock Redis client
            mock_redis_client = AsyncMock()
            mock_redis_client.ping = AsyncMock(return_value=True)
            mock_redis_config.get_redis_client = MagicMock(
                return_value=mock_redis_client
            )

            # Mock database session
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(return_value=MagicMock())
            mock_session.execute.return_value.scalar_one = MagicMock(return_value=1)
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # Make request
            response = client.get("/api/health")

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert "redis" in data
            assert "db" in data
            assert data["redis"]["ok"] is True
            assert data["db"]["ok"] is True

    @pytest.mark.asyncio
    async def test_health_endpoint_redis_failure(self, client):
        """Test that the health endpoint returns failure when Redis is down."""
        with (
            patch("slidespeaker.routes.health_routes.RedisConfig") as mock_redis_config,
            patch("slidespeaker.routes.health_routes.get_session") as mock_get_session,
        ):
            # Mock Redis client to fail
            mock_redis_client = AsyncMock()
            mock_redis_client.ping = AsyncMock(
                side_effect=Exception("Redis connection failed")
            )
            mock_redis_config.get_redis_client = MagicMock(
                return_value=mock_redis_client
            )

            # Mock database session
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(return_value=MagicMock())
            mock_session.execute.return_value.scalar_one = MagicMock(return_value=1)
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # Make request
            response = client.get("/api/health")

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert "redis" in data
            assert "db" in data
            assert data["redis"]["ok"] is False
            assert data["db"]["ok"] is True

    @pytest.mark.asyncio
    async def test_health_endpoint_database_failure(self, client):
        """Test that the health endpoint returns failure when database is down."""
        with (
            patch("slidespeaker.routes.health_routes.RedisConfig") as mock_redis_config,
            patch("slidespeaker.routes.health_routes.get_session") as mock_get_session,
        ):
            # Mock Redis client
            mock_redis_client = AsyncMock()
            mock_redis_client.ping = AsyncMock(return_value=True)
            mock_redis_config.get_redis_client = MagicMock(
                return_value=mock_redis_client
            )

            # Mock database session to fail
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(
                side_effect=Exception("Database connection failed")
            )
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # Make request
            response = client.get("/api/health")

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert "redis" in data
            assert "db" in data
            assert data["redis"]["ok"] is True
            assert data["db"]["ok"] is False
