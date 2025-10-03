"""
Language configuration routes.

This module provides API endpoints for retrieving supported languages
and their locale information for the presentation processing system.
"""

from fastapi import APIRouter, Depends

from slidespeaker.configs.locales import locale_utils
from slidespeaker.utils.auth import require_authenticated_user

router = APIRouter(
    prefix="/api",
    tags=["languages"],
    dependencies=[Depends(require_authenticated_user)],
)


@router.get("/languages")
async def get_supported_languages() -> list[dict[str, str]]:
    """
    Get list of all supported languages with locale codes and display names
    """
    return locale_utils.get_supported_languages()
