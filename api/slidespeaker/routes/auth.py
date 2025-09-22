"""
Authentication routes for Google OAuth login.
"""

from __future__ import annotations

from typing import Any

from authlib.integrations.starlette_client import OAuth  # type: ignore[import-untyped]
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from starlette.config import Config as StarletteConfig

from slidespeaker.configs.config import config
from slidespeaker.core.session_manager import SessionManager
from slidespeaker.repository.user import create_user, get_user_by_email, get_user_by_id

# Initialize OAuth
starlette_config = StarletteConfig(
    environ={
        "GOOGLE_CLIENT_ID": config.google_client_id or "",
        "GOOGLE_CLIENT_SECRET": config.google_client_secret or "",
    }
)

oauth = OAuth(starlette_config)

# Register Google OAuth
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile",
    },
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/login")
async def login(request: Request) -> RedirectResponse:
    """Initiate Google OAuth login flow."""
    if not config.google_client_id or not config.google_client_secret:
        raise HTTPException(
            status_code=500,
            detail=(
                "Google OAuth is not configured. Please set GOOGLE_CLIENT_ID "
                "and GOOGLE_CLIENT_SECRET in your environment variables."
            ),
        )

    redirect_uri = config.google_redirect_uri
    return await oauth.google.authorize_redirect(request, redirect_uri)  # type: ignore[no-any-return]


@router.get("/callback")
async def auth_callback(request: Request) -> RedirectResponse:
    """Handle Google OAuth callback and create user session."""
    try:
        # Exchange authorization code for access token
        token = await oauth.google.authorize_access_token(request)

        # Get user info from Google
        user_info = token.get("userinfo")
        if not user_info:
            raise HTTPException(
                status_code=400, detail="Failed to get user info from Google"
            )

        # Extract user data
        google_user_data = {
            "id": user_info.get("sub"),
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "picture": user_info.get("picture"),
        }

        # Check if user exists in database
        user = await get_user_by_email(google_user_data["email"])

        # If user doesn't exist, create new user
        if not user:
            user = await create_user(google_user_data)

        # Create session for the user
        session_manager = SessionManager()
        session_token = await session_manager.create_session(user["id"])

        # Redirect back to frontend with session token
        redirect_url = f"{config.google_redirect_uri}?session_token={session_token}"
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Authentication failed: {str(e)}"
        ) from e


@router.get("/logout")
async def logout(request: Request) -> dict[str, str]:
    """Logout user by clearing session."""
    # Get session token from request (in a real implementation, this would come from a cookie or header)
    session_token = request.query_params.get("session_token")

    if session_token:
        session_manager = SessionManager()
        await session_manager.destroy_session(session_token)

    return {"message": "Logged out successfully"}


@router.get("/user")
async def get_current_user(request: Request) -> dict[str, Any]:
    """Get current authenticated user info."""
    # Get session token from request (in a real implementation, this would come from a cookie or header)
    session_token = request.query_params.get("session_token")

    if not session_token:
        raise HTTPException(status_code=401, detail="Session token required")

    # Verify session token and get user ID
    session_manager = SessionManager()
    session_data = await session_manager.get_session(session_token)

    if not session_data:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    user_id = session_data["user_id"]

    # Get user data from database
    user = await get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
