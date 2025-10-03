"""
Subtitle download routes for serving generated subtitle files.

This module provides API endpoints for downloading and streaming generated
subtitle files in both SRT and VTT formats.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse

from slidespeaker.configs.config import config, get_storage_provider
from slidespeaker.configs.locales import locale_utils
from slidespeaker.storage import StorageProvider
from slidespeaker.utils.auth import require_authenticated_user

from .download_utils import file_id_from_task

router = APIRouter(
    prefix="/api",
    tags=["subtitle_downloads"],
    dependencies=[Depends(require_authenticated_user)],
)


async def _get_subtitle_language(
    task_id: str, language: str | None = None
) -> tuple[str, str]:
    """Get the subtitle language for a task, with fallback chain.

    Returns:
        tuple of (file_id, locale_code)
    """
    # If explicit language provided, use it
    if language:
        return "", locale_utils.get_locale_code(language)

    # Try to get from database first
    try:
        from slidespeaker.repository.task import get_task as db_get_task

        row = await db_get_task(task_id)
        if row:
            lang = row.get("subtitle_language") or row.get("voice_language")
            if isinstance(lang, str) and lang:
                return "", locale_utils.get_locale_code(lang)
    except Exception:
        pass

    # Fallback to state
    file_id = await file_id_from_task(task_id)
    try:
        from slidespeaker.core.state_manager import state_manager

        st = await state_manager.get_state(file_id)
        if st:
            lang = st.get("subtitle_language") or st.get("voice_language")
            if isinstance(lang, str) and lang:
                return file_id, locale_utils.get_locale_code(lang)
    except Exception:
        pass

    # Default to English
    return file_id, locale_utils.get_locale_code("english")


@router.get("/tasks/{task_id}/subtitles/srt")
async def get_srt_subtitles_by_task(
    task_id: str, language: str | None = None
) -> Response:
    """Serve SRT subtitle file for a task."""
    sp: StorageProvider = get_storage_provider()

    # Get language and file_id
    file_id, locale_code = await _get_subtitle_language(task_id, language)
    if not file_id:
        file_id = await file_id_from_task(task_id)

    # Task-id-based filename only
    task_key = f"{task_id}_{locale_code}.srt"
    if sp.file_exists(task_key):
        subtitle_content = sp.download_bytes(task_key)
        return Response(
            content=subtitle_content,
            media_type="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename=presentation_{task_id}_{locale_code}.srt",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language, Content-Type",
                "Cache-Control": "public, max-age=3600",
            },
        )

    # Fallback: local state paths if upload missing
    from slidespeaker.core.state_manager import state_manager

    st2 = await state_manager.get_state(file_id)
    if st2 and "steps" in st2:
        data_block = None
        if st2["steps"].get("generate_subtitles"):
            data_block = st2["steps"]["generate_subtitles"].get("data")
        elif st2["steps"].get("generate_pdf_subtitles"):
            data_block = st2["steps"]["generate_pdf_subtitles"].get("data")
        data = data_block or {}
        files = data.get("subtitle_files") or []
        import os

        candidate = next((p for p in files if p.endswith(f"_{locale_code}.srt")), None)
        if not candidate:
            candidate = next((p for p in files if p.lower().endswith(".srt")), None)
        if candidate and os.path.exists(candidate):
            return FileResponse(
                candidate,
                media_type="text/plain",
                filename=f"presentation_{task_id}_{locale_code}.srt",
                headers={
                    "Content-Disposition": f"inline; filename=presentation_{task_id}_{locale_code}.srt"
                },
            )
    raise HTTPException(status_code=404, detail="SRT subtitles not found")


@router.get("/tasks/{task_id}/subtitles/srt/download")
async def download_srt_subtitles_by_task(
    task_id: str, language: str | None = None
) -> Any:
    """Download SRT with attachment disposition (task-based)."""
    file_id = await file_id_from_task(task_id)

    # Get language
    file_id_check, locale_code = await _get_subtitle_language(task_id, language)
    if not file_id_check:
        file_id_check = file_id

    # Resolve object_key (task-id naming only)
    object_key = f"{task_id}_{locale_code}.srt"
    sp: StorageProvider = get_storage_provider()
    if not sp.file_exists(object_key):
        raise HTTPException(status_code=404, detail="SRT subtitles not found")

    if config.storage_provider == "local":
        actual = config.output_dir / object_key
        return FileResponse(
            str(actual),
            media_type="text/plain",
            filename=f"presentation_{task_id}_{locale_code}.srt",
            headers={
                "Content-Disposition": f"attachment; filename=presentation_{task_id}_{locale_code}.srt",
                "Access-Control-Allow-Origin": "*",
            },
        )

    url = sp.get_file_url(
        object_key,
        expires_in=600,
        content_disposition=f"attachment; filename=presentation_{task_id}_{locale_code}.srt",
        content_type="text/plain",
    )
    return Response(
        status_code=307, headers={"Location": url, "Access-Control-Allow-Origin": "*"}
    )


@router.get("/tasks/{task_id}/subtitles/vtt")
async def get_vtt_subtitles_by_task(
    task_id: str, language: str | None = None
) -> Response:
    """Serve VTT subtitle file for a task."""
    sp: StorageProvider = get_storage_provider()

    # Get language and file_id
    file_id, locale_code = await _get_subtitle_language(task_id, language)
    if not file_id:
        file_id = await file_id_from_task(task_id)

    # Task-id-based filename only
    task_key = f"{task_id}_{locale_code}.vtt"
    if sp.file_exists(task_key):
        subtitle_content = sp.download_bytes(task_key)
        return Response(
            content=subtitle_content,
            media_type="text/vtt",
            headers={
                "Content-Disposition": f"inline; filename=presentation_{task_id}_{locale_code}.vtt",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language, Content-Type",
                "Cache-Control": "public, max-age=3600",
            },
        )

    # Fallback: local state paths if upload missing
    from slidespeaker.core.state_manager import state_manager

    st2 = await state_manager.get_state(file_id)
    if st2 and "steps" in st2:
        step = (
            st2["steps"].get("generate_subtitles")
            or st2["steps"].get("generate_pdf_subtitles")
            or {}
        )
        data = step.get("data") or {}
        files = data.get("subtitle_files") or []
        import os

        candidate = next((p for p in files if p.endswith(f"_{locale_code}.vtt")), None)
        if not candidate:
            candidate = next((p for p in files if p.lower().endswith(".vtt")), None)
        if candidate and os.path.exists(candidate):
            return FileResponse(
                candidate,
                media_type="text/vtt",
                filename=f"presentation_{task_id}_{locale_code}.vtt",
                headers={
                    "Content-Disposition": f"inline; filename=presentation_{task_id}_{locale_code}.vtt"
                },
            )
    raise HTTPException(status_code=404, detail="VTT subtitles not found")


@router.get("/tasks/{task_id}/subtitles/vtt/download")
async def download_vtt_subtitles_by_task(
    task_id: str, language: str | None = None
) -> Any:
    """Download VTT with attachment disposition (task-based)."""
    file_id = await file_id_from_task(task_id)

    # Get language
    file_id_check, locale_code = await _get_subtitle_language(task_id, language)
    if not file_id_check:
        file_id_check = file_id

    # Resolve object_key (task-id naming only)
    object_key = f"{task_id}_{locale_code}.vtt"
    sp: StorageProvider = get_storage_provider()
    if not sp.file_exists(object_key):
        raise HTTPException(status_code=404, detail="VTT subtitles not found")

    if config.storage_provider == "local":
        actual = config.output_dir / object_key
        return FileResponse(
            str(actual),
            media_type="text/vtt",
            filename=f"presentation_{task_id}_{locale_code}.vtt",
            headers={
                "Content-Disposition": f"attachment; filename=presentation_{task_id}_{locale_code}.vtt",
                "Access-Control-Allow-Origin": "*",
            },
        )

    url = sp.get_file_url(
        object_key,
        expires_in=600,
        content_disposition=f"attachment; filename=presentation_{task_id}_{locale_code}.vtt",
        content_type="text/vtt",
    )
    return Response(
        status_code=307, headers={"Location": url, "Access-Control-Allow-Origin": "*"}
    )


@router.options("/tasks/{task_id}/subtitles/vtt")
async def options_vtt_subtitles_by_task(task_id: str) -> Response:
    """OPTIONS endpoint for VTT subtitles (CORS preflight)."""
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language, Content-Type",
        "Access-Control-Max-Age": "86400",
    }
    return Response(status_code=200, headers=headers)


@router.head("/tasks/{task_id}/subtitles/vtt")
async def head_vtt_subtitles_by_task(
    task_id: str, language: str | None = None
) -> Response:
    """HEAD endpoint to check if VTT subtitles exist."""
    # Get language
    _, locale_code = await _get_subtitle_language(task_id, language)

    sp: StorageProvider = get_storage_provider()
    # Check existence by task-id only (no file-id fallback)
    exists = sp.file_exists(f"{task_id}_{locale_code}.vtt")
    if not exists:
        return Response(status_code=404)
    headers = {
        "Content-Type": "text/vtt",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language, Content-Type",
        "Cache-Control": "public, max-age=3600",
    }
    return Response(status_code=200, headers=headers)


@router.head("/tasks/{task_id}/subtitles/srt")
async def head_srt_subtitles_by_task(
    task_id: str, language: str | None = None
) -> Response:
    """HEAD endpoint to check if SRT subtitles exist."""
    # Get language
    _, locale_code = await _get_subtitle_language(task_id, language)

    sp: StorageProvider = get_storage_provider()
    exists = sp.file_exists(f"{task_id}_{locale_code}.srt")
    if not exists:
        return Response(status_code=404)
    headers = {
        "Content-Type": "text/plain",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language, Content-Type",
        "Cache-Control": "public, max-age=3600",
    }
    return Response(status_code=200, headers=headers)
