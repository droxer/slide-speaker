"""
Session management for user authentication.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta
from typing import Any

from itsdangerous import BadSignature, SignatureExpired, TimestampSigner

from slidespeaker.configs.config import config
from slidespeaker.configs.redis_config import RedisConfig


class SessionManager:
    def __init__(self) -> None:
        self.redis_client = RedisConfig.get_redis_client()
        self.signer = TimestampSigner(
            config.google_client_secret or secrets.token_urlsafe(32)
        )
        self.session_expiry = timedelta(hours=24)  # 24 hour session expiry

    async def create_session(self, user_id: str) -> str:
        """Create a new session for a user and return the session token."""
        # Generate a random session ID
        session_id = secrets.token_urlsafe(32)

        # Create session data
        session_data = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
        }

        # Store session in Redis with expiry
        session_key = f"session:{session_id}"
        await self.redis_client.setex(
            session_key,
            int(self.session_expiry.total_seconds()),
            json.dumps(session_data),
        )

        # Sign the session ID to create a secure token
        signed_token = self.signer.sign(session_id)

        # Ensure return value is str
        return (
            signed_token.decode("utf-8")
            if isinstance(signed_token, bytes)
            else str(signed_token)
        )

    async def get_session(self, signed_token: str) -> dict[str, Any] | None:
        """Get session data from a signed token."""
        try:
            # Unsign the token to get the session ID
            session_id = self.signer.unsign(
                signed_token, max_age=int(self.session_expiry.total_seconds())
            )

            # Ensure session_id is string
            session_id_str = (
                session_id.decode("utf-8")
                if isinstance(session_id, bytes)
                else str(session_id)
            )

            # Get session data from Redis
            session_key = f"session:{session_id_str}"
            session_data = await self.redis_client.get(session_key)

            if session_data:
                if isinstance(session_data, bytes):
                    session_data = session_data.decode("utf-8")
                loaded_data: dict[str, Any] = json.loads(session_data)
                return loaded_data
            return None
        except (BadSignature, SignatureExpired):
            return None

    async def destroy_session(self, signed_token: str) -> bool:
        """Destroy a session by its signed token."""
        try:
            # Unsign the token to get the session ID
            session_id = self.signer.unsign(signed_token)

            # Ensure session_id is string
            session_id_str = (
                session_id.decode("utf-8")
                if isinstance(session_id, bytes)
                else str(session_id)
            )

            # Delete session from Redis
            session_key = f"session:{session_id_str}"
            result = await self.redis_client.delete(session_key)

            return bool(result > 0)
        except (BadSignature, SignatureExpired):
            return False

    async def refresh_session(self, signed_token: str) -> str | None:
        """Refresh a session's expiry time and return a new token."""
        session_data = await self.get_session(signed_token)
        if not session_data:
            return None

        # Extract session ID from the token
        try:
            session_id = self.signer.unsign(signed_token)
            # Ensure session_id is string
            session_id_str = (
                session_id.decode("utf-8")
                if isinstance(session_id, bytes)
                else str(session_id)
            )

            # Refresh the session in Redis
            session_key = f"session:{session_id_str}"
            await self.redis_client.expire(
                session_key, int(self.session_expiry.total_seconds())
            )

            # Return the same token since it's still valid
            return signed_token
        except (BadSignature, SignatureExpired):
            return None
