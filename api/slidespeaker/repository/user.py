"""
User repository backed by Postgres.

Persists users and handles user-related operations via SQLAlchemy.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from slidespeaker.auth.passwords import hash_password, verify_password
from slidespeaker.configs.db import get_session
from slidespeaker.configs.locales import locale_utils
from slidespeaker.core.models import User


def _row_to_dict(
    row: User | None, *, include_password: bool = False
) -> dict[str, Any] | None:
    if row is None:
        return None

    data: dict[str, Any] = {
        "id": row.id,
        "email": row.email,
        "name": row.name,
        "picture": row.picture,
        "preferred_language": row.preferred_language,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
    if include_password:
        data["password_hash"] = row.password_hash
    return data


async def get_user_by_email(email: str) -> dict[str, Any] | None:
    """Fetch a user by email.

    Returns a plain dict or None when not found.
    """
    from sqlalchemy import select

    async with get_session() as s:
        row = (
            await s.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        return _row_to_dict(row)


async def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    """Fetch a user by ID.

    Returns a plain dict or None when not found.
    """
    from sqlalchemy import select

    async with get_session() as s:
        row = (
            await s.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()
        return _row_to_dict(row)


async def get_user_credentials(email: str) -> dict[str, Any] | None:
    """Fetch a user including password hash for authentication."""

    from sqlalchemy import select

    async with get_session() as s:
        row = (
            await s.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        return _row_to_dict(row, include_password=True)


async def create_user(user_data: dict[str, Any]) -> dict[str, Any]:
    """Create a new user.

    Returns the created user as a dict.
    """

    async with get_session() as s:
        now = datetime.now()
        preferred_language = locale_utils.normalize_language(
            user_data.get("preferred_language")
        )
        row = User(
            id=user_data["id"],
            email=user_data["email"],
            name=user_data.get("name"),
            picture=user_data.get("picture"),
            password_hash=user_data.get("password_hash"),
            preferred_language=preferred_language,
            created_at=now,
            updated_at=now,
        )
        s.add(row)
        await s.commit()

        # Return the created user
        created = _row_to_dict(row)
        if created is None:
            raise RuntimeError("Failed to materialize created user")
        return created


async def update_user(user_id: str, **fields: Any) -> dict[str, Any] | None:
    """Update user fields by user_id.

    Returns the updated user as a dict or None if not found.
    """
    from sqlalchemy import update as sa_update

    allowed = {"name", "picture", "updated_at", "password_hash", "preferred_language"}
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


async def create_user_with_password(
    email: str,
    password: str,
    *,
    name: str | None = None,
    picture: str | None = None,
    preferred_language: str | None = None,
) -> dict[str, Any]:
    """Create a user with a password hash. Raises ValueError if the email exists."""

    existing = await get_user_by_email(email)
    if existing:
        raise ValueError("User already exists")

    user_id = str(uuid4())
    hashed = hash_password(password)
    now = datetime.now()

    async with get_session() as s:
        normalized_language = locale_utils.normalize_language(preferred_language)
        row = User(
            id=user_id,
            email=email,
            name=name,
            picture=picture,
            password_hash=hashed,
            preferred_language=normalized_language,
            created_at=now,
            updated_at=now,
        )
        s.add(row)
        await s.commit()
        await s.refresh(row)
        created = _row_to_dict(row)
        if created is None:
            raise RuntimeError("Failed to materialize created user")
        return created


async def set_user_password(user_id: str, password: str) -> dict[str, Any] | None:
    """Update the password hash for the given user."""

    hashed = hash_password(password)
    return await update_user(user_id, password_hash=hashed)


async def verify_user_credentials(email: str, password: str) -> dict[str, Any] | None:
    """Return the user dict if credentials are valid, else None."""

    record = await get_user_credentials(email)
    if not record:
        return None

    hashed = record.pop("password_hash", None)
    if not hashed or not verify_password(password, hashed):
        return None
    return record


async def upsert_oauth_user(user_data: dict[str, Any]) -> dict[str, Any]:
    """Create or update a user record based on OAuth profile data."""

    email = user_data.get("email")
    if not email:
        raise ValueError("email is required")

    name = user_data.get("name")
    picture = user_data.get("picture")
    user_id = user_data.get("id") or str(uuid4())
    now = datetime.now()

    from sqlalchemy import select

    async with get_session() as s:
        existing = (
            await s.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()

        if existing:
            changed = False
            if name is not None and existing.name != name:
                existing.name = name
                changed = True
            if picture is not None and existing.picture != picture:
                existing.picture = picture
                changed = True
            if changed:
                existing.updated_at = now
                await s.commit()
            result = _row_to_dict(existing)
            if result is None:
                raise RuntimeError("Existing user disappeared during update")
            return result

        normalized_language = locale_utils.normalize_language(
            user_data.get("preferred_language")
        )
        row = User(
            id=user_id,
            email=email,
            name=name,
            picture=picture,
            password_hash=None,
            preferred_language=normalized_language,
            created_at=now,
            updated_at=now,
        )
        s.add(row)
        await s.commit()
        await s.refresh(row)
        created = _row_to_dict(row)
        if created is None:
            raise RuntimeError("Failed to materialize created user")
        return created


async def update_user_profile(
    user_id: str,
    *,
    name: str | None,
    preferred_language: str,
) -> dict[str, Any] | None:
    return await update_user(
        user_id,
        name=name,
        preferred_language=preferred_language,
    )


async def list_users(*, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    """Return a paginated list of users sorted by creation time (newest first)."""

    from sqlalchemy import select

    async with get_session() as s:
        stmt = select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
        rows = (await s.execute(stmt)).scalars().all()
        serialized: list[dict[str, Any]] = []
        for row in rows:
            data = _row_to_dict(row)
            if data is not None:
                serialized.append(data)
        return serialized


async def delete_user(user_id: str) -> bool:
    """Delete a user by id. Returns True if a row was removed."""

    from sqlalchemy import delete

    async with get_session() as s:
        result = await s.execute(delete(User).where(User.id == user_id))
        await s.commit()
        return result.rowcount > 0
