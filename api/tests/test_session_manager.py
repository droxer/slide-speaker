"""
Unit tests for the session manager module.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from slidespeaker.core.session_manager import SessionManager


class TestSessionManager:
    """Test cases for the SessionManager class."""

    @pytest.fixture
    def session_manager(self):
        """Create a SessionManager instance with mocked dependencies."""
        with (
            patch("slidespeaker.core.session_manager.RedisConfig"),
            patch("slidespeaker.core.session_manager.config"),
        ):
            manager = SessionManager()
            manager.redis_client = AsyncMock()
            manager.signer = MagicMock()
            return manager

    def test_init(self, session_manager):
        """Test that SessionManager can be instantiated."""
        assert isinstance(session_manager, SessionManager)

    @pytest.mark.asyncio
    async def test_create_session_success(self, session_manager):
        """Test that create_session successfully creates a session."""
        # Mock dependencies
        session_manager.signer.sign = MagicMock(return_value=b"signed_token")

        # Call the method
        result = await session_manager.create_session("test_user_id")

        # Verify the result
        assert result == "signed_token"

        # Verify Redis set was called
        session_manager.redis_client.setex.assert_called_once()

        # Verify signer was called
        session_manager.signer.sign.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_success(self, session_manager):
        """Test that get_session successfully retrieves session data."""
        # Mock Redis response
        mock_session_data = (
            '{"user_id": "test_user_id", "created_at": "2023-01-01T00:00:00"}'
        )
        session_manager.redis_client.get = AsyncMock(return_value=mock_session_data)
        session_manager.signer.unsign = MagicMock(return_value=b"test_user_id")

        # Call the method
        result = await session_manager.get_session("test_session_token")

        # Verify the result
        assert result is not None
        assert result["user_id"] == "test_user_id"

        # Verify Redis get was called
        session_manager.redis_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_nonexistent(self, session_manager):
        """Test that get_session returns None for nonexistent sessions."""
        # Mock Redis response
        session_manager.redis_client.get = AsyncMock(return_value=None)
        session_manager.signer.unsign = MagicMock(return_value=b"test_user_id")

        # Call the method
        result = await session_manager.get_session("test_session_token")

        # Verify the result
        assert result is None

        # Verify Redis get was called
        session_manager.redis_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_expired_session(self, session_manager):
        """Test that get_session handles expired sessions gracefully."""
        # Mock dependencies to raise SignatureExpired exception
        from itsdangerous import SignatureExpired

        session_manager.signer.unsign = MagicMock(
            side_effect=SignatureExpired("Token expired")
        )

        # Call the method
        result = await session_manager.get_session("expired_session_token")

        # Verify the result
        assert result is None

        # Verify signer unsign was called
        session_manager.signer.unsign.assert_called_once()

    @pytest.mark.asyncio
    async def test_destroy_session_success(self, session_manager):
        """Test that destroy_session successfully destroys a session."""
        # Mock dependencies
        session_manager.signer.unsign = MagicMock(return_value=b"test_user_id")
        session_manager.redis_client.delete = AsyncMock(return_value=1)

        # Call the method
        result = await session_manager.destroy_session("test_session_token")

        # Verify the result
        assert result is True

        # Verify Redis delete was called
        session_manager.redis_client.delete.assert_called_once()

        # Verify signer unsign was called
        session_manager.signer.unsign.assert_called_once()

    @pytest.mark.asyncio
    async def test_destroy_session_invalid_token(self, session_manager):
        """Test that destroy_session handles invalid tokens gracefully."""
        # Mock dependencies to raise BadSignature exception
        from itsdangerous import BadSignature

        session_manager.signer.unsign = MagicMock(
            side_effect=BadSignature("Invalid token")
        )

        # Call the method
        result = await session_manager.destroy_session("invalid_session_token")

        # Verify the result
        assert result is False

        # Verify signer unsign was called
        session_manager.signer.unsign.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_session_success(self, session_manager):
        """Test that refresh_session successfully refreshes a session."""
        # Mock dependencies
        session_manager.signer.unsign = MagicMock(return_value=b"test_user_id")
        session_manager.redis_client.get = AsyncMock(
            return_value=b'{"user_id": "test_user_id"}'
        )
        session_manager.redis_client.expire = AsyncMock(return_value=True)
        # Note: The refresh_session method returns the same token, not a new one

        # Call the method
        result = await session_manager.refresh_session("test_session_token")

        # Verify the result (should return the same token)
        assert result == "test_session_token"

    @pytest.mark.asyncio
    async def test_refresh_session_invalid_token(self, session_manager):
        """Test that refresh_session handles invalid tokens gracefully."""
        # Mock dependencies to raise BadSignature exception
        from itsdangerous import BadSignature

        session_manager.signer.unsign = MagicMock(
            side_effect=BadSignature("Invalid token")
        )

        # Call the method
        result = await session_manager.refresh_session("invalid_session_token")

        # Verify the result
        assert result is None

        # Verify signer unsign was called
        session_manager.signer.unsign.assert_called_once()
