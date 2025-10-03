"""
Audio download routes for serving generated audio files.

This module provides API endpoints for downloading and streaming generated
audio files with appropriate content types and headers.
"""

import os
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse

from slidespeaker.configs.config import config, get_storage_provider
from slidespeaker.storage import StorageProvider
from slidespeaker.utils.auth import require_authenticated_user

from .download_utils import (
    file_id_from_task,
    final_audio_object_keys,
    get_audio_files_from_state,
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
    for key in final_audio_object_keys(file_id):
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
                        headers={
                            "Content-Type": "audio/mpeg",
                            "Content-Length": str(file_size),
                            "Accept-Ranges": "bytes",
                            "Access-Control-Allow-Origin": "*",
                            "Cache-Control": "no-cache, no-store, must-revalidate",
                            "Content-Disposition": f"inline; filename=presentation_{file_id}.mp3",
                        },
                    )
            except Exception:
                pass
        else:
            # Cloud: try proxying the object key without relying on HEAD permissions
            try:
                if config.proxy_cloud_media:
                    return await proxy_cloud_media(key, "audio/mpeg", None)
                # If proxy disabled, attempt redirect
                url = sp.get_file_url(
                    key,
                    expires_in=300,
                    content_disposition=f"inline; filename=presentation_{file_id}.mp3",
                    content_type="audio/mpeg",
                )
                return Response(
                    status_code=307,
                    headers={
                        "Location": url,
                        "Content-Type": "audio/mpeg",
                        "Accept-Ranges": "bytes",
                        "Cache-Control": "no-cache, no-store, must-revalidate",
                        "Access-Control-Allow-Origin": "*",
                    },
                )
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
                headers={
                    # Serve inline so <audio> can play concatenated bytes
                    "Content-Type": "audio/mpeg",
                    "Accept-Ranges": "bytes",
                    "Content-Disposition": f"inline; filename=presentation_{file_id}.mp3",
                    "Access-Control-Allow-Origin": "*",
                    "Cache-Control": "no-cache",
                },
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
            headers={
                "Content-Type": "audio/mpeg",
                "Content-Length": str(file_size),
                "Accept-Ranges": "bytes",
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Content-Disposition": f"inline; filename=presentation_{file_id}.mp3",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail="Final audio not found") from e


@router.get("/tasks/{task_id}/audio/tracks")
async def list_audio_files_by_task(task_id: str) -> dict[str, Any]:
    """List audio tracks using task_id and emit task-based URLs."""
    from slidespeaker.core.state_manager import state_manager as sm

    file_id = await file_id_from_task(task_id)
    state = await sm.get_state(file_id)
    if not state:
        raise HTTPException(status_code=404, detail="State not found")

    # Collect audio files from state
    audio_files = await get_audio_files_from_state(file_id)
    file_ext = (state.get("file_ext") or "").lower()
    label = "Chapter" if file_ext == ".pdf" else "Slide"

    tracks: list[dict[str, Any]] = []
    for i, path in enumerate(audio_files):
        tracks.append(
            {
                "index": i + 1,
                "name": f"{label} {i + 1}",
                "api_url": f"/api/tasks/{task_id}/audio/{i + 1}",
                "path": path,
            }
        )

    return {
        "task_id": task_id,
        "file_id": file_id,
        "language": state.get("voice_language", "english"),
        "count": len(tracks),
        "tracks": tracks,
    }


@router.get("/tasks/{task_id}/audio")
async def get_final_audio_by_task(task_id: str, request: Request) -> Any:
    """Serve final audio by task, preferring task-id-based object keys.

    Avoid pre-checks that can fail on cloud providers with restricted HEAD permissions.
    Try task-id first; on 404, fall back to file-id mapping.
    """
    sp: StorageProvider = get_storage_provider()
    file_id = await file_id_from_task(task_id)

    # Check for audio files using the same logic as downloads endpoint
    # First check task-id based key
    if sp.file_exists(f"{task_id}.mp3"):
        task_key = f"{task_id}.mp3"
        # Found task-id based audio file, use it directly
        if config.storage_provider == "local":
            actual = config.output_dir / task_key
            try:
                if actual.exists() and actual.is_file():
                    # Get file size for Content-Length header
                    file_size = actual.stat().st_size

                    # Handle Range requests for proper audio streaming
                    range_header = request.headers.get("range") or request.headers.get(
                        "Range"
                    )
                    if range_header:
                        try:
                            # Parse Range: bytes=start-end
                            units, _, rng = range_header.partition("=")
                            start_s, _, end_s = rng.partition("-")
                            if units.strip().lower() != "bytes":
                                raise ValueError("Unsupported range unit")
                            start = int(start_s) if start_s else 0
                            end = int(end_s) if end_s else file_size - 1
                            start = max(0, start)
                            end = min(end, file_size - 1)
                            if start > end:
                                # Invalid range
                                raise ValueError("Invalid range")
                            length = end - start + 1

                            def iter_file(
                                chunk_size: int = 1024 * 256,
                            ) -> Iterator[bytes]:
                                with open(str(actual), "rb") as f:
                                    f.seek(start)
                                    remaining = length
                                    while remaining > 0:
                                        data = f.read(min(chunk_size, remaining))
                                        if not data:
                                            break
                                        remaining -= len(data)
                                        yield data

                            return StreamingResponse(
                                iter_file(),
                                status_code=206,  # Partial Content
                                headers={
                                    "Content-Type": "audio/mpeg",
                                    "Content-Length": str(length),
                                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                                    "Accept-Ranges": "bytes",
                                    "Access-Control-Allow-Origin": "*",
                                    "Cache-Control": "no-cache, no-store, must-revalidate",
                                },
                            )
                        except Exception:
                            # Malformed range header, fall back to full file
                            pass

                    # No range request or range parsing failed, serve full file
                    return FileResponse(
                        str(actual),
                        media_type="audio/mpeg",
                        filename=f"presentation_{task_id}.mp3",
                        headers={
                            "Content-Type": "audio/mpeg",
                            "Content-Length": str(file_size),
                            "Accept-Ranges": "bytes",
                            "Access-Control-Allow-Origin": "*",
                            "Cache-Control": "no-cache, no-store, must-revalidate",
                            "Content-Disposition": f"inline; filename=presentation_{task_id}.mp3",
                        },
                    )
            except Exception:
                pass
        else:
            # Cloud: try proxying the object key without relying on HEAD permissions
            try:
                if config.proxy_cloud_media:
                    return await proxy_cloud_media(task_key, "audio/mpeg", None)
                # If proxy disabled, attempt redirect
                url = sp.get_file_url(
                    task_key,
                    expires_in=300,
                    content_disposition=f"inline; filename=presentation_{task_id}.mp3",
                    content_type="audio/mpeg",
                )
                return Response(
                    status_code=307,
                    headers={
                        "Location": url,
                        "Content-Type": "audio/mpeg",
                        "Accept-Ranges": "bytes",
                        "Cache-Control": "no-cache, no-store, must-revalidate",
                        "Access-Control-Allow-Origin": "*",
                    },
                )
            except HTTPException as e:
                # Continue to fallback on 404/403; re-raise others
                if e.status_code not in (403, 404):
                    raise
            except Exception:
                # Continue to fallback on any provider error
                pass
    else:
        # Check file-id based keys (same as downloads endpoint)
        from .download_utils import final_audio_object_keys

        for key in final_audio_object_keys(file_id):
            if sp.file_exists(key):
                # Found file-id based audio file, use the file-based logic
                return await get_final_audio(file_id, request)

    # Final fallback to file-id based logic
    return await get_final_audio(file_id, request)


@router.get("/tasks/{task_id}/audio/download")
async def download_final_audio_by_task(task_id: str) -> Any:
    """Download endpoint for the final MP3 with attachment disposition."""
    sp: StorageProvider = get_storage_provider()
    # Resolve best key (prefer task-id, then file-id variants)
    if sp.file_exists(f"{task_id}.mp3"):
        object_key = f"{task_id}.mp3"
    else:
        file_id = await file_id_from_task(task_id)
        keys = final_audio_object_keys(file_id)
        found = next((k for k in keys if sp.file_exists(k)), None)
        if not found:
            raise HTTPException(status_code=404, detail="Final audio not found")
        object_key = found

    if config.storage_provider == "local":
        actual = config.output_dir / object_key
        return FileResponse(
            str(actual),
            media_type="audio/mpeg",
            filename=f"presentation_{task_id}.mp3",
            headers={
                "Content-Disposition": f"attachment; filename=presentation_{task_id}.mp3",
                "Access-Control-Allow-Origin": "*",
            },
        )

    # Cloud: redirect with attachment disposition
    url = sp.get_file_url(
        object_key,
        expires_in=600,
        content_disposition=f"attachment; filename=presentation_{task_id}.mp3",
        content_type="audio/mpeg",
    )
    return Response(
        status_code=307, headers={"Location": url, "Access-Control-Allow-Origin": "*"}
    )


@router.get("/tasks/{task_id}/audio/{index}")
async def get_audio_file_by_task(task_id: str, index: int) -> Any:
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
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Cache-Control": "public, max-age=3600",
            "Content-Disposition": f"inline; filename={task_id}_track_{index}.mp3",
        },
    )
