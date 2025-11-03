"""
Subtitle download routes for serving generated subtitle files.

This module provides API endpoints for downloading and streaming generated
subtitle files in both SRT and VTT formats.
"""

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse

from slidespeaker.auth import require_authenticated_user
from slidespeaker.configs.config import config, get_storage_provider
from slidespeaker.configs.locales import locale_utils
from slidespeaker.core.state_manager import state_manager
from slidespeaker.storage import StorageProvider
from slidespeaker.storage.paths import (
    object_key_from_uri,
    output_object_key,
    resolve_output_base_id,
)

from .download_helpers import build_headers, file_id_from_task

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


def _unique_strings(values: list[str | None]) -> list[str]:
    """Deduplicate string values while preserving order."""
    return [
        value
        for value in dict.fromkeys(values)
        if isinstance(value, str) and value.strip()
    ]


def _matches_locale(path: str, locale_code: str, ext: str) -> bool:
    """Check if a path ends with a locale-specific suffix."""
    lower_path = path.lower()
    ext_lower = f".{ext.lower()}"
    if not lower_path.endswith(ext_lower):
        return False
    code = locale_code.lower()
    return lower_path.endswith(f"_{code}{ext_lower}") or lower_path.endswith(
        f"-{code}{ext_lower}"
    )


def _collect_candidate_storage_keys(
    task_id: str,
    file_id: str,
    locale_code: str,
    ext: str,
    state: dict[str, Any] | None,
) -> list[str]:
    """Collect potential storage keys for a subtitle asset."""
    base_ids = [task_id, file_id]
    if state:
        tid = state.get("task_id")
        if isinstance(tid, str):
            base_ids.append(tid)
        try:
            resolved = resolve_output_base_id(file_id, state=state)
            base_ids.append(resolved)
        except Exception:
            pass

    keys: list[str | None] = []
    for base in _unique_strings(base_ids):
        keys.append(output_object_key(base, "subtitles", f"{locale_code}.{ext}"))

    keys.append(f"{task_id}_{locale_code}.{ext}")

    if state:
        steps = state.get("steps") or {}
        step = (
            steps.get("generate_subtitles") or steps.get("generate_pdf_subtitles") or {}
        )
        data = step.get("data")
        if isinstance(data, dict):
            for key in data.get("storage_keys") or []:
                keys.append(key if isinstance(key, str) else None)
            for uri in data.get("storage_uris") or []:
                if isinstance(uri, str):
                    keys.append(object_key_from_uri(uri))
        artifacts = state.get("artifacts")
        if isinstance(artifacts, dict):
            subtitles_artifacts = artifacts.get("subtitles")
            if isinstance(subtitles_artifacts, dict):
                entry = subtitles_artifacts.get(locale_code)
                if isinstance(entry, dict):
                    keys.append(entry.get("storage_key"))
                    keys.append(object_key_from_uri(entry.get("storage_uri")))

    return _unique_strings(keys)  # type: ignore[arg-type]


def _collect_candidate_local_paths(
    state: dict[str, Any] | None, locale_code: str, ext: str
) -> list[str]:
    """Collect local fallback paths for subtitles from state."""
    paths: list[str | None] = []
    if state:
        steps = state.get("steps") or {}
        step = (
            steps.get("generate_subtitles") or steps.get("generate_pdf_subtitles") or {}
        )
        data = step.get("data")
        if isinstance(data, dict):
            for path in data.get("subtitle_files") or []:
                paths.append(path if isinstance(path, str) else None)
        artifacts = state.get("artifacts")
        if isinstance(artifacts, dict):
            subtitles_artifacts = artifacts.get("subtitles")
            if isinstance(subtitles_artifacts, dict):
                entry = subtitles_artifacts.get(locale_code)
                if isinstance(entry, dict):
                    paths.append(entry.get("local_path"))
    filtered = [
        path
        for path in paths
        if isinstance(path, str)
        and path.strip()
        and path.lower().endswith(f".{ext.lower()}")
    ]
    return _unique_strings(filtered)  # type: ignore[arg-type]


def _select_local_path(
    candidates: list[str],
    locale_code: str,
    ext: str,
) -> str | None:
    """Select the best matching local subtitle path."""
    for path in candidates:
        if _matches_locale(path, locale_code, ext) and os.path.exists(path):
            return path
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


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
    try:
        state = await state_manager.get_state(file_id)
    except Exception:
        state = None

    candidate_keys = _collect_candidate_storage_keys(
        task_id, file_id, locale_code, "srt", state
    )
    for key in candidate_keys:
        try:
            subtitle_content = sp.download_bytes(key)
            return Response(
                content=subtitle_content,
                media_type="text/plain",
                headers=build_headers(
                    request,
                    content_type="text/plain",
                    disposition=f"attachment; filename=presentation_{task_id}_{locale_code}.srt",
                    cache_control="public, max-age=3600, must-revalidate",
                ),
            )
        except FileNotFoundError:
            continue
        except Exception:
            continue

    # Fallback: local state paths if upload missing
    local_candidates = _collect_candidate_local_paths(state, locale_code, "srt")
    selected = _select_local_path(local_candidates, locale_code, "srt")
    if selected:
        return FileResponse(
            selected,
            media_type="text/plain",
            filename=f"presentation_{task_id}_{locale_code}.srt",
            headers=build_headers(
                request,
                content_type="text/plain",
                disposition=f"inline; filename=presentation_{task_id}_{locale_code}.srt",
                cache_control="public, max-age=3600, must-revalidate",
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

    sp: StorageProvider = get_storage_provider()
    try:
        state = await state_manager.get_state(file_id_check)
    except Exception:
        state = None

    candidate_keys = _collect_candidate_storage_keys(
        task_id, file_id_check, locale_code, "srt", state
    )
    object_key: str | None = None
    for key in candidate_keys:
        try:
            if sp.file_exists(key):
                object_key = key
                break
        except Exception:
            continue

    if not object_key:
        local_candidates = _collect_candidate_local_paths(state, locale_code, "srt")
        selected = _select_local_path(local_candidates, locale_code, "srt")
        if selected:
            return FileResponse(
                selected,
                media_type="text/plain",
                filename=f"presentation_{task_id}_{locale_code}.srt",
                headers=build_headers(
                    request,
                    content_type="text/plain",
                    disposition=f"attachment; filename=presentation_{task_id}_{locale_code}.srt",
                ),
            )
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

    # For OSS storage, avoid setting content_type to prevent header override errors
    get_file_url_kwargs = {
        "object_key": object_key,
        "expires_in": 600,
        "content_disposition": f"attachment; filename=presentation_{task_id}_{locale_code}.srt",
    }

    # Only set content_type for non-OSS providers
    if config.storage_provider != "oss":
        get_file_url_kwargs["content_type"] = "text/plain"

    url = sp.get_file_url(**get_file_url_kwargs)
    headers = {"Location": url}
    origin = request.headers.get("origin") or request.headers.get("Origin")
    if origin:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    else:
        headers["Access-Control-Allow-Origin"] = "*"
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
    try:
        state = await state_manager.get_state(file_id)
    except Exception:
        state = None

    candidate_keys = _collect_candidate_storage_keys(
        task_id, file_id, locale_code, "vtt", state
    )
    for key in candidate_keys:
        try:
            subtitle_content = sp.download_bytes(key)
            return Response(
                content=subtitle_content,
                media_type="text/vtt",
                headers=build_headers(
                    request,
                    content_type="text/vtt",
                    disposition=f"inline; filename=presentation_{task_id}_{locale_code}.vtt",
                    cache_control="public, max-age=3600, must-revalidate",
                ),
            )
        except FileNotFoundError:
            continue
        except Exception:
            continue

    local_candidates = _collect_candidate_local_paths(state, locale_code, "vtt")
    selected = _select_local_path(local_candidates, locale_code, "vtt")
    if selected:
        return FileResponse(
            selected,
            media_type="text/vtt",
            filename=f"presentation_{task_id}_{locale_code}.vtt",
            headers=build_headers(
                request,
                content_type="text/vtt",
                disposition=f"inline; filename=presentation_{task_id}_{locale_code}.vtt",
                cache_control="public, max-age=3600, must-revalidate",
            ),
        )
    raise HTTPException(status_code=404, detail="VTT subtitles not found")


@router.get("/tasks/{task_id}/subtitles/vtt/download")
async def download_vtt_subtitles_by_task(
    task_id: str, request: Request, language: str | None = None
) -> Any:
    """Download VTT with attachment disposition (task-based)."""
    file_id = await file_id_from_task(task_id)

    # Get language
    file_id_check, locale_code = await _get_subtitle_language(task_id, language)
    if not file_id_check:
        file_id_check = file_id

    sp: StorageProvider = get_storage_provider()
    try:
        state = await state_manager.get_state(file_id_check)
    except Exception:
        state = None

    candidate_keys = _collect_candidate_storage_keys(
        task_id, file_id_check, locale_code, "vtt", state
    )
    object_key: str | None = None
    for key in candidate_keys:
        try:
            if sp.file_exists(key):
                object_key = key
                break
        except Exception:
            continue

    if not object_key:
        local_candidates = _collect_candidate_local_paths(state, locale_code, "vtt")
        selected = _select_local_path(local_candidates, locale_code, "vtt")
        if selected:
            return FileResponse(
                selected,
                media_type="text/vtt",
                filename=f"presentation_{task_id}_{locale_code}.vtt",
                headers={
                    "Content-Disposition": f"attachment; filename=presentation_{task_id}_{locale_code}.vtt",
                    "Access-Control-Allow-Origin": "*",
                },
            )
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

    # For OSS storage, avoid setting content_type to prevent header override errors
    get_file_url_kwargs = {
        "object_key": object_key,
        "expires_in": 600,
        "content_disposition": f"attachment; filename=presentation_{task_id}_{locale_code}.vtt",
    }

    # Only set content_type for non-OSS providers
    if config.storage_provider != "oss":
        get_file_url_kwargs["content_type"] = "text/vtt"

    url = sp.get_file_url(**get_file_url_kwargs)
    headers = {"Location": url}
    origin = request.headers.get("origin") or request.headers.get("Origin")
    if origin:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    else:
        headers["Access-Control-Allow-Origin"] = "*"
    return Response(status_code=307, headers=headers)


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
