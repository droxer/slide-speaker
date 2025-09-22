"""
User repository backed by Postgres.

Persists users and handles user-related operations via SQLAlchemy.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from slidespeaker.configs.db import get_session
from slidespeaker.core.models import User


async def get_user_by_email(email: str) -> dict[str, Any] | None:
    """Fetch a user by email.

    Returns a plain dict or None when not found.
    """
    from sqlalchemy import select

    async with get_session() as s:
        row = (
            await s.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if not row:
            return None
        return {
            "id": row.id,
            "email": row.email,
            "name": row.name,
            "picture": row.picture,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }


async def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    """Fetch a user by ID.

    Returns a plain dict or None when not found.
    """
    from sqlalchemy import select

    async with get_session() as s:
        row = (
            await s.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()
        if not row:
            return None
        return {
            "id": row.id,
            "email": row.email,
            "name": row.name,
            "picture": row.picture,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }


async def create_user(user_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new user.

    Returns the created user as a dict.
    """

    async with get_session() as s:
        now = datetime.now()
        row = User(
            id=user_data["id"],
            email=user_data["email"],
            name=user_data.get("name"),
            picture=user_data.get("picture"),
            created_at=now,
            updated_at=now,
        )
        s.add(row)
        await s.commit()

        # Return the created user
        return {
            "id": row.id,
            "email": row.email,
            "name": row.name,
            "picture": row.picture,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }


async def update_user(user_id: str, **fields: Any) -> dict[str, Any] | None:
    """Update user fields by user_id.

    Returns the updated user as a dict or None if not found.
    """
    from sqlalchemy import update as sa_update

    allowed = {"name", "picture", "updated_at"}
    vals: dict[str, Any] = {k: v for k, v in fields.items() if k in allowed}
    if "updated_at" not in vals:
        vals["updated_at"] = datetime.now()
    if not vals:
        # If no valid fields to update, just return the current user
        return await get_user_by_id(user_id)

    async with get_session() as s:
        result = await s.execute(
            sa_update(User).where(User.id == user_id).values(**vals)
        )
        await s.commit()

        if result.rowcount > 0:
            return await get_user_by_id(user_id)
        return None
