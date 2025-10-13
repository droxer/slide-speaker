"""
Subtitle download routes for serving generated subtitle files.

This module provides API endpoints for downloading and streaming generated
subtitle files in both SRT and VTT formats.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse

from slidespeaker.auth import require_authenticated_user
from slidespeaker.configs.config import config, get_storage_provider
from slidespeaker.configs.locales import locale_utils
from slidespeaker.storage import StorageProvider
from slidespeaker.storage.paths import object_key_from_uri, output_object_key

from .download_helpers import build_headers, check_file_exists, file_id_from_task

router = APIRouter(
    prefix="/api",
    tags=["subtitles"],
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
    task_id: str, request: Request, language: str | None = None
) -> Response:
    """Serve SRT subtitle file for a task."""

    # Get language and file_id
    file_id, locale_code = await _get_subtitle_language(task_id, language)
    if not file_id:
        file_id = await file_id_from_task(task_id)

    sp: StorageProvider = get_storage_provider()

    candidate_keys = [
        output_object_key(task_id, "subtitles", f"{locale_code}.srt"),
        output_object_key(file_id, "subtitles", f"{locale_code}.srt"),
        f"{task_id}_{locale_code}.srt",
    ]
    object_key = next((k for k in candidate_keys if check_file_exists(k)), None)
    if object_key:
        subtitle_content = sp.download_bytes(object_key)
        return Response(
            content=subtitle_content,
            media_type="text/plain",
            headers=build_headers(
                request,
                content_type="text/plain",
                disposition=f"attachment; filename=presentation_{task_id}_{locale_code}.srt",
            ),
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
                headers=build_headers(
                    request,
                    content_type="text/plain",
                    disposition=f"inline; filename=presentation_{task_id}_{locale_code}.srt",
                ),
            )
        # Check artifacts map for stored URIs/keys
        artifacts = st2.get("artifacts") if isinstance(st2, dict) else None
        if isinstance(artifacts, dict):
            subtitles_artifacts = artifacts.get("subtitles")
            if isinstance(subtitles_artifacts, dict):
                entry = subtitles_artifacts.get(locale_code)
                if isinstance(entry, dict):
                    storage_key = entry.get("storage_key")
                    storage_uri = entry.get("storage_uri")
                    local_path = entry.get("local_path")
                    key = storage_key or object_key_from_uri(storage_uri)
                    if key:
                        try:
                            subtitle_content = sp.download_bytes(key)
                            return Response(
                                content=subtitle_content,
                                media_type="text/plain",
                                headers=build_headers(
                                    request,
                                    content_type="text/plain",
                                    disposition=f"inline; filename=presentation_{task_id}_{locale_code}.srt",
                                ),
                            )
                        except Exception:
                            pass
                    if local_path and os.path.exists(local_path):
                        return FileResponse(
                            local_path,
                            media_type="text/plain",
                            filename=f"presentation_{task_id}_{locale_code}.srt",
                            headers=build_headers(
                                request,
                                content_type="text/plain",
                                disposition=f"inline; filename=presentation_{task_id}_{locale_code}.srt",
                            ),
                        )
    raise HTTPException(status_code=404, detail="SRT subtitles not found")


@router.get("/tasks/{task_id}/subtitles/srt/download")
async def download_srt_subtitles_by_task(
    task_id: str, request: Request, language: str | None = None
) -> Any:
    """Download SRT with attachment disposition (task-based)."""
    file_id = await file_id_from_task(task_id)

    # Get language
    file_id_check, locale_code = await _get_subtitle_language(task_id, language)
    if not file_id_check:
        file_id_check = file_id

    # Resolve object_key (task-id naming only)
    object_key = next(
        (
            k
            for k in [
                output_object_key(task_id, "subtitles", f"{locale_code}.srt"),
                output_object_key(file_id_check, "subtitles", f"{locale_code}.srt"),
                f"{task_id}_{locale_code}.srt",
            ]
            if check_file_exists(k)
        ),
        None,
    )
    sp: StorageProvider = get_storage_provider()
    if not object_key:
        raise HTTPException(status_code=404, detail="SRT subtitles not found")

    if config.storage_provider == "local":
        actual = config.output_dir / object_key
        return FileResponse(
            str(actual),
            media_type="text/plain",
            filename=f"presentation_{task_id}_{locale_code}.srt",
            headers=build_headers(
                request,
                content_type="text/plain",
                disposition=f"attachment; filename=presentation_{task_id}_{locale_code}.srt",
            ),
        )

    url = sp.get_file_url(
        object_key,
        expires_in=600,
        content_disposition=f"attachment; filename=presentation_{task_id}_{locale_code}.srt",
        content_type="text/plain",
    )
    headers = {"Location": url}
    origin = request.headers.get("origin") or request.headers.get("Origin")
    if origin:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return Response(status_code=307, headers=headers)


@router.get("/tasks/{task_id}/subtitles/vtt")
async def get_vtt_subtitles_by_task(
    task_id: str, request: Request, language: str | None = None
) -> Response:
    """Serve VTT subtitle file for a task."""

    # Get language and file_id
    file_id, locale_code = await _get_subtitle_language(task_id, language)
    if not file_id:
        file_id = await file_id_from_task(task_id)

    sp: StorageProvider = get_storage_provider()

    # Task-id-based filename only
    candidate_keys = [
        output_object_key(task_id, "subtitles", f"{locale_code}.vtt"),
        output_object_key(file_id, "subtitles", f"{locale_code}.vtt"),
        f"{task_id}_{locale_code}.vtt",
    ]
    object_key = next((k for k in candidate_keys if check_file_exists(k)), None)
    if object_key:
        subtitle_content = sp.download_bytes(object_key)
        return Response(
            content=subtitle_content,
            media_type="text/vtt",
            headers=build_headers(
                request,
                content_type="text/vtt",
                disposition=f"inline; filename=presentation_{task_id}_{locale_code}.vtt",
            ),
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
                headers=build_headers(
                    request,
                    content_type="text/vtt",
                    disposition=f"inline; filename=presentation_{task_id}_{locale_code}.vtt",
                ),
            )
        # Check artifacts map
        artifacts = st2.get("artifacts") if isinstance(st2, dict) else None
        if isinstance(artifacts, dict):
            subtitles_artifacts = artifacts.get("subtitles")
            if isinstance(subtitles_artifacts, dict):
                entry = subtitles_artifacts.get(locale_code)
                if isinstance(entry, dict):
                    storage_key = entry.get("storage_key")
                    storage_uri = entry.get("storage_uri")
                    local_path = entry.get("local_path")
                    key = storage_key or object_key_from_uri(storage_uri)
                    if key:
                        try:
                            subtitle_content = sp.download_bytes(key)
                            return Response(
                                content=subtitle_content,
                                media_type="text/vtt",
                                headers=build_headers(
                                    request,
                                    content_type="text/vtt",
                                    disposition=f"inline; filename=presentation_{task_id}_{locale_code}.vtt",
                                ),
                            )
                        except Exception:
                            pass
                    if local_path and os.path.exists(local_path):
                        return FileResponse(
                            local_path,
                            media_type="text/vtt",
                            filename=f"presentation_{task_id}_{locale_code}.vtt",
                            headers=build_headers(
                                request,
                                content_type="text/vtt",
                                disposition=f"inline; filename=presentation_{task_id}_{locale_code}.vtt",
                            ),
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
    object_key = next(
        (
            k
            for k in [
                output_object_key(task_id, "subtitles", f"{locale_code}.vtt"),
                output_object_key(file_id_check, "subtitles", f"{locale_code}.vtt"),
                f"{task_id}_{locale_code}.vtt",
            ]
            if check_file_exists(k)
        ),
        None,
    )
    sp: StorageProvider = get_storage_provider()
    if not object_key:
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
    file_id, locale_code = await _get_subtitle_language(task_id, language)
    if not file_id:
        file_id = await file_id_from_task(task_id)

    from .download_helpers import check_file_exists

    candidates = [
        output_object_key(task_id, "subtitles", f"{locale_code}.vtt"),
        output_object_key(file_id, "subtitles", f"{locale_code}.vtt"),
        f"{task_id}_{locale_code}.vtt",
    ]
    exists = any(check_file_exists(key) for key in candidates)
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
    file_id, locale_code = await _get_subtitle_language(task_id, language)
    if not file_id:
        file_id = await file_id_from_task(task_id)

    from .download_helpers import check_file_exists

    candidates = [
        output_object_key(task_id, "subtitles", f"{locale_code}.srt"),
        output_object_key(file_id, "subtitles", f"{locale_code}.srt"),
        f"{task_id}_{locale_code}.srt",
    ]
    exists = any(check_file_exists(key) for key in candidates)
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
