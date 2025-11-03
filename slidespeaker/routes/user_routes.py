"""Routes for user profile management."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from slidespeaker.auth import require_authenticated_user
from slidespeaker.configs.locales import locale_utils
from slidespeaker.repository.user import get_user_by_id, update_user_profile

router = APIRouter(
    prefix="/api/users",
    tags=["users"],
    dependencies=[Depends(require_authenticated_user)],
)


class ProfileResponse(BaseModel):
    user: dict[str, object]


class UpdateProfilePayload(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    preferred_language: str | None = Field(default=None, max_length=64)
    preferred_theme: str | None = Field(default=None, max_length=32)


async def _resolve_current_user(decoded_token: dict[str, object]) -> dict[str, object]:
    user_section = (
        decoded_token.get("user") if isinstance(decoded_token, dict) else None
    )
    user_id = None
    if isinstance(user_section, dict):
        user_id = user_section.get("id")
    if not user_id and isinstance(decoded_token, dict):
        raw_sub = decoded_token.get("sub")
        if isinstance(raw_sub, str):
            user_id = raw_sub
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid session"
        )

    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user not found"
        )
    return user


@router.get("/me", response_model=ProfileResponse)
async def get_profile(
    current: Annotated[dict[str, object], Depends(require_authenticated_user)],
) -> ProfileResponse:
    user = await _resolve_current_user(current)
    return ProfileResponse(user=user)


@router.patch("/me", response_model=ProfileResponse)
async def update_profile(
    payload: UpdateProfilePayload,
    current: Annotated[dict[str, object], Depends(require_authenticated_user)],
) -> ProfileResponse:
    user = await _resolve_current_user(current)

    user_id = user.get("id")
    if not isinstance(user_id, str):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="invalid user identifier",
        )

    new_language = payload.preferred_language
    if new_language is not None:
        normalized_lang = locale_utils.normalize_language(new_language)
    else:
        existing_lang = user.get("preferred_language")
        normalized_lang = locale_utils.normalize_language(
            existing_lang if isinstance(existing_lang, str) else None
        )

    current_name = user.get("name")
    effective_name: str | None
    if payload.name is not None:
        effective_name = payload.name
    elif isinstance(current_name, str):
        effective_name = current_name
    else:
        effective_name = None

    # Handle theme preference
    current_theme = user.get("preferred_theme")
    effective_theme: str | None
    if payload.preferred_theme is not None:
        effective_theme = payload.preferred_theme
    elif isinstance(current_theme, str):
        effective_theme = current_theme
    else:
        effective_theme = None

    updated = await update_user_profile(
        user_id,
        name=effective_name,
        preferred_language=normalized_lang,
        preferred_theme=effective_theme,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="update failed"
        )

    return ProfileResponse(user=cast(dict[str, object], updated))
