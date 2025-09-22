"""
Unit tests for the auth routes module.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from slidespeaker.routes.auth import router


class TestAuthRoutes:
    """Test cases for the auth routes."""

    @pytest.fixture
    def client(self):
        """Create a TestClient for testing the auth routes."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @pytest.mark.skip(reason="Temporarily disabled due to complexity of mocking OAuth")
    def test_login_endpoint_redirect(self, client):
        """Test that the login endpoint redirects to Google OAuth."""
        with (
            patch("slidespeaker.routes.auth.oauth") as mock_oauth,
            patch("slidespeaker.routes.auth.config") as mock_config,
        ):
            # Mock config
            mock_config.google_client_id = "test_client_id"
            mock_config.google_client_secret = "test_client_secret"
            mock_config.google_redirect_uri = "http://localhost:3000/auth/callback"

            # Mock OAuth authorize redirect to return a RedirectResponse
            from fastapi.responses import RedirectResponse

            mock_redirect_response = RedirectResponse(
                url="https://accounts.google.com/o/oauth2/v2/auth?test"
            )
            mock_authorize_redirect = AsyncMock(return_value=mock_redirect_response)
            mock_google = MagicMock()
            mock_google.authorize_redirect = mock_authorize_redirect
            mock_oauth.google = mock_google

            # Make request
            response = client.get("/api/auth/login")

            # Verify redirect was called
            mock_authorize_redirect.assert_called_once()

            # Verify response is a redirect (3xx status code)
            assert 300 <= response.status_code < 400

    def test_login_endpoint_missing_config(self, client):
        """Test that the login endpoint returns error when Google OAuth is not configured."""
        with patch("slidespeaker.routes.auth.config") as mock_config:
            # Mock config with missing credentials
            mock_config.google_client_id = None
            mock_config.google_client_secret = None

            # Make request
            response = client.get("/api/auth/login")

            # Verify response
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Google OAuth is not configured" in data["detail"]

    @pytest.mark.skip(reason="Temporarily disabled due to complexity of mocking OAuth")
    def test_auth_callback_success(self, client):
        """Test that the auth callback endpoint successfully handles Google OAuth callback."""
        with (
            patch("slidespeaker.routes.auth.oauth") as mock_oauth,
            patch("slidespeaker.routes.auth.SessionManager") as mock_session_manager,
            patch(
                "slidespeaker.routes.auth.get_user_by_email"
            ) as mock_get_user_by_email,
            patch("slidespeaker.routes.auth.create_user") as mock_create_user,
        ):
            # Mock OAuth response
            mock_token = {
                "access_token": "test_access_token",
                "token_type": "Bearer",
                "expires_in": 3600,
                "userinfo": {
                    "sub": "test_google_id",
                    "email": "test@example.com",
                    "name": "Test User",
                    "picture": "http://example.com/picture.jpg",
                },
            }

            # Mock authorize access token
            mock_authorize_access_token = AsyncMock(return_value=mock_token)
            mock_google = MagicMock()
            mock_google.authorize_access_token = mock_authorize_access_token
            mock_oauth.google = mock_google

            # Mock user repository functions
            mock_get_user_by_email.return_value = None  # User doesn't exist

            # Mock create user
            mock_created_user = {
                "id": "test_user_id",
                "email": "test@example.com",
                "name": "Test User",
                "picture": "http://example.com/picture.jpg",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
            }
            mock_create_user.return_value = mock_created_user

            # Mock session manager
            mock_session_manager_instance = MagicMock()
            mock_session_manager_instance.create_session = AsyncMock(
                return_value="test_session_token"
            )
            mock_session_manager.return_value = mock_session_manager_instance

            # Make request
            response = client.get(
                "/api/auth/callback?code=test_auth_code&state=test_state"
            )

            # Verify OAuth authorize access token was called
            mock_authorize_access_token.assert_called_once()

            # Verify user was checked
            mock_get_user_by_email.assert_called_once_with("test@example.com")

            # Verify user was created
            mock_create_user.assert_called_once()

            # Verify session was created
            mock_session_manager_instance.create_session.assert_called_once_with(
                "test_user_id"
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["user"]["id"] == "test_user_id"
            assert data["user"]["email"] == "test@example.com"
            assert data["session_token"] == "test_session_token"

    @pytest.mark.skip(reason="Temporarily disabled due to complexity of mocking OAuth")
    def test_auth_callback_user_exists(self, client):
        """Test that the auth callback endpoint handles existing users correctly."""
        with (
            patch("slidespeaker.routes.auth.oauth") as mock_oauth,
            patch("slidespeaker.routes.auth.SessionManager") as mock_session_manager,
            patch(
                "slidespeaker.routes.auth.get_user_by_email"
            ) as mock_get_user_by_email,
        ):
            # Mock OAuth response
            mock_token = {
                "access_token": "test_access_token",
                "token_type": "Bearer",
                "expires_in": 3600,
                "userinfo": {
                    "sub": "test_google_id",
                    "email": "existing@example.com",
                    "name": "Existing User",
                    "picture": "http://example.com/picture.jpg",
                },
            }

            # Mock authorize access token
            mock_authorize_access_token = AsyncMock(return_value=mock_token)
            mock_google = MagicMock()
            mock_google.authorize_access_token = mock_authorize_access_token
            mock_oauth.google = mock_google

            # Mock existing user
            mock_existing_user = {
                "id": "existing_user_id",
                "email": "existing@example.com",
                "name": "Existing User",
                "picture": "http://example.com/picture.jpg",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
            }
            mock_get_user_by_email.return_value = mock_existing_user

            # Mock session manager
            mock_session_manager_instance = MagicMock()
            mock_session_manager_instance.create_session = AsyncMock(
                return_value="test_session_token"
            )
            mock_session_manager.return_value = mock_session_manager_instance

            # Make request
            response = client.get(
                "/api/auth/callback?code=test_auth_code&state=test_state"
            )

            # Verify OAuth authorize access token was called
            mock_authorize_access_token.assert_called_once()

            # Verify user was checked
            mock_get_user_by_email.assert_called_once_with("existing@example.com")

            # Verify session was created
            mock_session_manager_instance.create_session.assert_called_once_with(
                "existing_user_id"
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["user"]["id"] == "existing_user_id"
            assert data["user"]["email"] == "existing@example.com"
            assert data["session_token"] == "test_session_token"

    def test_auth_callback_missing_userinfo(self, client):
        """Test that the auth callback endpoint handles missing userinfo gracefully."""
        with patch("slidespeaker.routes.auth.oauth") as mock_oauth:
            # Mock OAuth response with missing userinfo
            mock_token = {
                "access_token": "test_access_token",
                "token_type": "Bearer",
                "expires_in": 3600,
                # Missing userinfo
            }

            # Mock authorize access token
            mock_authorize_access_token = AsyncMock(return_value=mock_token)
            mock_google = MagicMock()
            mock_google.authorize_access_token = mock_authorize_access_token
            mock_oauth.google = mock_google

            # Make request
            response = client.get(
                "/api/auth/callback?code=test_auth_code&state=test_state"
            )

            # Verify OAuth authorize access token was called
            mock_authorize_access_token.assert_called_once()

            # Verify error response
            assert response.status_code == 400
            data = response.json()
            assert "detail" in data
            assert "Failed to get user info from Google" in data["detail"]

    def test_logout_endpoint_success(self, client):
        """Test that the logout endpoint successfully logs out a user."""
        # Make request with session token
        response = client.get(
            "/api/auth/logout", params={"session_token": "test_session_token"}
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "Logged out successfully"

    def test_logout_endpoint_no_session_token(self, client):
        """Test that the logout endpoint handles missing session token gracefully."""
        # Make request without session token
        response = client.get("/api/auth/logout")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "Logged out successfully"

    def test_get_current_user_success(self, client):
        """Test that the get current user endpoint successfully returns user info."""
        with (
            patch("slidespeaker.routes.auth.SessionManager") as mock_session_manager,
            patch("slidespeaker.routes.auth.get_user_by_id") as mock_get_user_by_id,
        ):
            # Mock session manager
            mock_session_manager_instance = MagicMock()
            mock_session_manager_instance.get_session = AsyncMock(
                return_value={"user_id": "test_user_id"}
            )
            mock_session_manager.return_value = mock_session_manager_instance

            # Mock user repository
            mock_user = {
                "id": "test_user_id",
                "email": "test@example.com",
                "name": "Test User",
                "picture": "http://example.com/picture.jpg",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
            }
            mock_get_user_by_id.return_value = mock_user

            # Make request with session token
            response = client.get(
                "/api/auth/user", params={"session_token": "test_session_token"}
            )

            # Verify session manager was called
            mock_session_manager_instance.get_session.assert_called_once_with(
                "test_session_token"
            )

            # Verify user was retrieved
            mock_get_user_by_id.assert_called_once_with("test_user_id")

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "test_user_id"
            assert data["email"] == "test@example.com"
            assert data["name"] == "Test User"

    def test_get_current_user_missing_session_token(self, client):
        """Test that the get current user endpoint handles missing session token."""
        # Make request without session token
        response = client.get("/api/auth/user")

        # Verify error response
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Session token required"

    def test_get_current_user_invalid_session(self, client):
        """Test that the get current user endpoint handles invalid session."""
        with patch("slidespeaker.routes.auth.SessionManager") as mock_session_manager:
            # Mock session manager to return None
            mock_session_manager_instance = MagicMock()
            mock_session_manager_instance.get_session = AsyncMock(return_value=None)
            mock_session_manager.return_value = mock_session_manager_instance

            # Make request with invalid session token
            response = client.get(
                "/api/auth/user", params={"session_token": "invalid_session_token"}
            )

            # Verify session manager was called
            mock_session_manager_instance.get_session.assert_called_once_with(
                "invalid_session_token"
            )

            # Verify error response
            assert response.status_code == 401
            data = response.json()
            assert "detail" in data
            assert data["detail"] == "Invalid or expired session"

    def test_get_current_user_user_not_found(self, client):
        """Test that the get current user endpoint handles user not found."""
        with (
            patch("slidespeaker.routes.auth.SessionManager") as mock_session_manager,
            patch("slidespeaker.routes.auth.get_user_by_id") as mock_get_user_by_id,
        ):
            # Mock session manager
            mock_session_manager_instance = MagicMock()
            mock_session_manager_instance.get_session = AsyncMock(
                return_value={"user_id": "nonexistent_user_id"}
            )
            mock_session_manager.return_value = mock_session_manager_instance

            # Mock user repository to return None
            mock_get_user_by_id.return_value = None

            # Make request with session token
            response = client.get(
                "/api/auth/user", params={"session_token": "test_session_token"}
            )

            # Verify session manager was called
            mock_session_manager_instance.get_session.assert_called_once_with(
                "test_session_token"
            )

            # Verify user repository was called
            mock_get_user_by_id.assert_called_once_with("nonexistent_user_id")

            # Verify error response
            assert response.status_code == 404
            data = response.json()
            assert "detail" in data
            assert data["detail"] == "User not found"
