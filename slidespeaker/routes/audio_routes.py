"""
Audio download routes for serving generated audio files.

This module provides API endpoints for downloading and streaming generated
audio files with appropriate content types and headers.
"""

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse

from slidespeaker.auth import require_authenticated_user
from slidespeaker.configs.config import config, get_storage_provider
from slidespeaker.core.state_manager import state_manager
from slidespeaker.storage import StorageProvider

from .download_helpers import (
    build_headers,
    file_id_from_task,
    final_audio_object_keys,
    get_audio_files_from_state,
    iter_file,
    proxy_cloud_media,
    stream_concatenated_files,
)

router = APIRouter(
    prefix="/api",
    tags=["audio_downloads"],
    dependencies=[Depends(require_authenticated_user)],
)


async def get_final_audio(file_id: str, request: Request) -> Any:
    """Serve a single final audio output for the whole presentation.

    Resolution order:
    1) If a final audio file exists in storage, serve/redirect it.
    2) If local storage and no final file, concatenate per-slide audio on the fly.
    3) Otherwise, fall back to serving the last generated audio track.
    """
    sp: StorageProvider = get_storage_provider()

    # 1) Prebuilt final audio in storage
    state = await state_manager.get_state(file_id)
    task_hint = None
    if state and isinstance(state, dict):
        candidate = state.get("task_id")
        if isinstance(candidate, str) and candidate.strip():
            task_hint = candidate.strip()
        elif isinstance(state.get("task"), dict):
            candidate = state["task"].get("task_id")
            if isinstance(candidate, str) and candidate.strip():
                task_hint = candidate.strip()

    for key in final_audio_object_keys(file_id, task_id=task_hint):
        if config.storage_provider == "local":
            # Local FS: verify and serve directly
            actual = config.output_dir / key
            try:
                if actual.exists() and actual.is_file():
                    # Get file size for Content-Length header
                    file_size = actual.stat().st_size
                    return FileResponse(
                        str(actual),
                        media_type="audio/mpeg",
                        filename=f"presentation_{file_id}.mp3",
                        headers=build_headers(
                            request,
                            content_type="audio/mpeg",
                            content_length=file_size,
                            disposition=f"inline; filename=presentation_{file_id}.mp3",
                        ),
                    )
            except Exception:
                pass
        else:
            # Cloud: try proxying the object key without relying on HEAD permissions
            try:
                if config.proxy_cloud_media:
                    origin = request.headers.get("origin") or request.headers.get(
                        "Origin"
                    )
                    return await proxy_cloud_media(
                        key,
                        "audio/mpeg",
                        None,
                        origin=origin,
                    )
                # If proxy disabled, attempt redirect
                url = sp.get_file_url(
                    key,
                    expires_in=300,
                    content_disposition=f"inline; filename=presentation_{file_id}.mp3",
                    content_type="audio/mpeg",
                )
                headers = build_headers(
                    request,
                    content_type="audio/mpeg",
                    cache_control="public, max-age=300, must-revalidate",
                )
                headers["Location"] = url
                return Response(status_code=307, headers=headers)
            except HTTPException as e:
                # Continue to next key on 404/403; re-raise others
                if e.status_code not in (403, 404):
                    raise
            except Exception:
                # Continue to next key on any provider error
                pass

    # 2) Local: concatenate audio files
    if config.storage_provider == "local":
        audio_files = await get_audio_files_from_state(file_id)
        if audio_files:
            return StreamingResponse(
                stream_concatenated_files(audio_files),
                media_type="audio/mpeg",
                headers=build_headers(
                    request,
                    content_type="audio/mpeg",
                    disposition=f"inline; filename=presentation_{file_id}.mp3",
                    cache_control="no-cache",
                ),
            )

    # 3) Fallback: last generated track (serve inline)
    audio_files = await get_audio_files_from_state(file_id)
    if not audio_files:
        raise HTTPException(status_code=404, detail="Final audio not found")
    try:
        actual_file_path = audio_files[-1]
        # Get file size for Content-Length header
        file_size = os.path.getsize(actual_file_path)
        return FileResponse(
            actual_file_path,
            media_type="audio/mpeg",
            filename=f"presentation_{file_id}.mp3",
            headers=build_headers(
                request,
                content_type="audio/mpeg",
                content_length=file_size,
                disposition=f"inline; filename=presentation_{file_id}.mp3",
            ),
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail="Final audio not found") from e


@router.get("/tasks/{task_id}/audio")
async def get_final_audio_by_task(task_id: str, request: Request) -> Any:
    """Serve final audio by task, preferring task-id-based object keys.

    Avoid pre-checks that can fail on cloud providers with restricted HEAD permissions.
    Try task-id first; on 404, fall back to file-id mapping.
    """
    from .download_helpers import check_file_exists

    sp: StorageProvider = get_storage_provider()
    file_id = await file_id_from_task(task_id)

    candidate_keys = final_audio_object_keys(file_id, task_id=task_id)
    found_key = next((k for k in candidate_keys if check_file_exists(k)), None)

    if found_key:
        if config.storage_provider == "local":
            actual = config.output_dir / found_key
            try:
                if actual.exists() and actual.is_file():
                    file_size = actual.stat().st_size
                    range_header = request.headers.get("range") or request.headers.get(
                        "Range"
                    )
                    if range_header:
                        try:
                            units, _, rng = range_header.partition("=")
                            start_s, _, end_s = rng.partition("-")
                            if units.strip().lower() != "bytes":
                                raise ValueError("Unsupported range unit")
                            start = int(start_s) if start_s else 0
                            end = int(end_s) if end_s else file_size - 1
                            start = max(0, start)
                            end = min(end, file_size - 1)
                            if start > end:
                                raise ValueError("Invalid range")
                            length = end - start + 1

                            headers = build_headers(
                                request,
                                content_type="audio/mpeg",
                                content_length=length,
                                cache_control="public, max-age=300, must-revalidate",
                            )
                            headers["Content-Range"] = (
                                f"bytes {start}-{end}/{file_size}"
                            )

                            return StreamingResponse(
                                iter_file(str(actual), start, length),
                                status_code=206,
                                headers=headers,
                            )
                        except Exception:
                            pass

                    return FileResponse(
                        str(actual),
                        media_type="audio/mpeg",
                        filename=f"presentation_{task_id}.mp3",
                        headers=build_headers(
                            request,
                            content_type="audio/mpeg",
                            content_length=file_size,
                            disposition=f"inline; filename=presentation_{task_id}.mp3",
                        ),
                    )
            except Exception:
                pass
        else:
            try:
                if config.proxy_cloud_media:
                    origin = request.headers.get("origin") or request.headers.get(
                        "Origin"
                    )
                    return await proxy_cloud_media(
                        found_key,
                        "audio/mpeg",
                        None,
                        origin=origin,
                    )
                # For OSS storage, avoid setting content_type to prevent header override errors
                get_file_url_kwargs = {
                    "object_key": found_key,
                    "expires_in": 300,
                    "content_disposition": f"inline; filename=presentation_{task_id}.mp3",
                }

                # Only set content_type for non-OSS providers
                if config.storage_provider != "oss":
                    get_file_url_kwargs["content_type"] = "audio/mpeg"

                url = sp.get_file_url(**get_file_url_kwargs)
                headers = build_headers(
                    request,
                    content_type="audio/mpeg",
                    cache_control="public, max-age=300, must-revalidate",
                )
                headers["Location"] = url
                return Response(status_code=307, headers=headers)
            except HTTPException as e:
                if e.status_code not in (403, 404):
                    raise
            except Exception:
                pass

    return await get_final_audio(file_id, request)


@router.get("/tasks/{task_id}/audio/download")
async def download_final_audio_by_task(task_id: str, request: Request) -> Any:
    """Download endpoint for the final MP3 with attachment disposition."""
    from .download_helpers import check_file_exists

    sp: StorageProvider = get_storage_provider()
    # Resolve best key (prefer task-id, then file-id variants)
    file_id = await file_id_from_task(task_id)
    keys = final_audio_object_keys(file_id, task_id=task_id)
    found = next((k for k in keys if check_file_exists(k)), None)
    if not found:
        raise HTTPException(status_code=404, detail="Final audio not found")
    object_key = found

    if config.storage_provider == "local":
        actual = config.output_dir / object_key
        return FileResponse(
            str(actual),
            media_type="audio/mpeg",
            filename=f"presentation_{task_id}.mp3",
            headers=build_headers(
                request,
                content_type="audio/mpeg",
                disposition=f"attachment; filename=presentation_{task_id}.mp3",
                cache_control="public, max-age=3600",
            ),
        )

    # Cloud: redirect with attachment disposition
    # For OSS storage, avoid setting content_type to prevent header override errors
    get_file_url_kwargs = {
        "object_key": object_key,
        "expires_in": 600,
        "content_disposition": f"attachment; filename=presentation_{task_id}.mp3",
    }

    # Only set content_type for non-OSS providers
    if config.storage_provider != "oss":
        get_file_url_kwargs["content_type"] = "audio/mpeg"

    url = sp.get_file_url(**get_file_url_kwargs)
    headers = {"Location": url}
    origin = request.headers.get("origin") or request.headers.get("Origin")
    if origin:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return Response(status_code=307, headers=headers)


@router.get("/tasks/{task_id}/audio/{index}")
async def get_audio_file_by_task(task_id: str, index: int, request: Request) -> Any:
    """Serve a single generated audio track by 1-based index (task-based)."""
    file_id = await file_id_from_task(task_id)
    audio_files = await get_audio_files_from_state(file_id)
    if not audio_files:
        raise HTTPException(status_code=404, detail="Audio not found")
    if index < 1 or index > len(audio_files):
        raise HTTPException(status_code=404, detail="Audio index out of range")
    actual_file_path = audio_files[index - 1]
    return FileResponse(
        actual_file_path,
        media_type="audio/mpeg",
        filename=f"{task_id}_track_{index}.mp3",
        headers=build_headers(
            request,
            content_type="audio/mpeg",
            disposition=f"inline; filename={task_id}_track_{index}.mp3",
            cache_control="public, max-age=3600",
        ),
    )
