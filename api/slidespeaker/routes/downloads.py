"""
Download routes for serving generated files.

This module provides API endpoints for downloading generated presentation videos
and subtitle files. It handles file serving with appropriate content types and headers.
"""

import urllib.request
from collections.abc import Iterator
from typing import Any
from urllib.error import HTTPError

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse

from slidespeaker.configs.config import config, get_storage_provider
from slidespeaker.storage import StorageProvider

router = APIRouter(prefix="/api", tags=["downloads"])


async def _get_audio_files_from_state(file_id: str) -> list[str]:
    """Helper to read generated audio file paths from state.

    Prefers PDF audio step when present; otherwise falls back to slide audio.
    """
    from slidespeaker.core.state_manager import state_manager as sm

    state = await sm.get_state(file_id)
    if not state or "steps" not in state:
        return []
    steps = state["steps"]
    # Prefer PDF audio when available
    if (
        "generate_pdf_audio" in steps
        and steps["generate_pdf_audio"].get("data") is not None
    ):
        data = steps["generate_pdf_audio"]["data"]
        return (
            data
            if isinstance(data, list)
            else ([data] if isinstance(data, str) else [])
        )
    # Fall back to slide audio
    if "generate_audio" in steps and steps["generate_audio"].get("data") is not None:
        data = steps["generate_audio"]["data"]
        return (
            data
            if isinstance(data, list)
            else ([data] if isinstance(data, str) else [])
        )
    return []


async def _file_id_from_task(task_id: str) -> str:
    """Resolve a file_id from a task_id using the task queue."""
    from slidespeaker.configs.redis_config import RedisConfig
    from slidespeaker.core.task_queue import task_queue

    # First, try the persisted mapping
    try:
        redis = RedisConfig.get_redis_client()
        mapped = await redis.get(f"ss:task2file:{task_id}")
        if mapped:
            return str(mapped)
    except Exception:
        pass

    # Fallback to the task payload if available
    task = await task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    file_id = (task.get("kwargs") or {}).get("file_id") or task.get("file_id")
    if not file_id or not isinstance(file_id, str):
        raise HTTPException(status_code=404, detail="File not found for task")
    return str(file_id)


def _stream_concatenated_files(
    paths: list[str], chunk_size: int = 1024 * 256
) -> Iterator[bytes]:
    """Generator to stream multiple files sequentially as one stream."""

    def iterator() -> Iterator[bytes]:
        for p in paths:
            with open(p, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

    return iterator()


def _final_audio_object_keys(file_id: str) -> list[str]:
    # Prefer new non-final naming first; include legacy for backward compatibility
    return [f"{file_id}.mp3", f"{file_id}_final_audio.mp3", f"{file_id}_final.mp3"]


@router.get("/tasks/{task_id}/downloads")
async def list_downloads(task_id: str) -> dict[str, Any]:
    """Provide a consolidated list of download links for a task.

    Includes video (inline and download), audio (inline and download),
    subtitles (available locales and formats), and transcript markdown.
    """
    sp: StorageProvider = get_storage_provider()
    file_id = await _file_id_from_task(task_id)
    items: list[dict[str, Any]] = []

    # Video
    if (
        sp.file_exists(f"{task_id}.mp4")
        or sp.file_exists(f"{file_id}.mp4")
        or sp.file_exists(f"{file_id}_final.mp4")
    ):
        items.append(
            {
                "type": "video",
                "url": f"/api/tasks/{task_id}/video",
                "download_url": f"/api/tasks/{task_id}/video/download",
            }
        )

    # Final audio
    audio_exists = any(
        sp.file_exists(k)
        for k in ([f"{task_id}.mp3"] + _final_audio_object_keys(file_id))
    )
    if audio_exists:
        items.append(
            {
                "type": "audio",
                "url": f"/api/tasks/{task_id}/audio",
                "download_url": f"/api/tasks/{task_id}/audio/download",
            }
        )

    # Subtitles by locale (detect existing)
    common_locales = [
        "zh-Hant",
        "zh-Hans",
        "en",
        "ja",
        "ko",
        "th",
        "es",
        "fr",
        "de",
        "it",
        "pt",
        "ru",
        "ar",
        "hi",
    ]
    seen_locales: set[str] = set()
    # Prefer task-id based keys
    for loc in common_locales:
        if sp.file_exists(f"{task_id}_{loc}.vtt") or sp.file_exists(
            f"{task_id}_{loc}.srt"
        ):
            seen_locales.add(loc)
    # Fallback to file-id based keys
    for loc in common_locales:
        if sp.file_exists(f"{file_id}_{loc}.vtt") or sp.file_exists(
            f"{file_id}_{loc}.srt"
        ):
            seen_locales.add(loc)

    for loc in sorted(seen_locales):
        # VTT
        items.append(
            {
                "type": "subtitles",
                "format": "vtt",
                "language": loc,
                "url": f"/api/tasks/{task_id}/subtitles/vtt?language={loc}",
                "download_url": f"/api/tasks/{task_id}/subtitles/vtt/download?language={loc}",
            }
        )
        # SRT
        items.append(
            {
                "type": "subtitles",
                "format": "srt",
                "language": loc,
                "url": f"/api/tasks/{task_id}/subtitles/srt?language={loc}",
                "download_url": f"/api/tasks/{task_id}/subtitles/srt/download?language={loc}",
            }
        )

    # Transcript (Markdown) always linkable; handler decides availability
    items.append(
        {
            "type": "transcript_markdown",
            "url": f"/api/tasks/{task_id}/transcripts/markdown",
        }
    )

    return {"task_id": task_id, "file_id": file_id, "items": items}


async def _proxy_cloud_media(
    object_key: str, media_type: str, range_header: str | None
) -> StreamingResponse:
    """Proxy a cloud object through the API, preferring SDK download.

    Uses provider SDK (download_bytes) to avoid signed URL issues; falls back
    to presigned URL streaming only if necessary. Range is best-effort.
    """
    sp: StorageProvider = get_storage_provider()

    # Attempt SDK download first (most reliable across providers)
    try:
        blob: bytes = sp.download_bytes(object_key)
        total = len(blob)

        # Handle Range header for seeking support
        if range_header:
            try:
                units, _, rng = range_header.partition("=")
                start_s, _, end_s = rng.partition("-")
                if units.strip().lower() != "bytes":
                    raise ValueError("Unsupported range unit")
                start = int(start_s) if start_s else 0
                end = int(end_s) if end_s else total - 1
                start = max(0, start)
                end = min(end, total - 1)
                if start > end:
                    # Invalid range
                    raise ValueError("Invalid range")
                length = end - start + 1
            except Exception:
                # Malformed; ignore range
                start = 0
                end = total - 1
                length = total

            def iter_slice(chunk_size: int = 1024 * 256) -> Iterator[bytes]:
                offset = start
                while offset <= end:
                    nxt = min(offset + chunk_size, end + 1)
                    yield blob[offset:nxt]
                    offset = nxt

            return StreamingResponse(
                iter_slice(),
                status_code=206,
                headers={
                    "Content-Type": media_type,
                    "Content-Length": str(length),
                    "Content-Range": f"bytes {start}-{end}/{total}",
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Access-Control-Allow-Origin": "*",
                },
            )

        # No Range: send full content with Accept-Ranges to allow client-side seeking after load
        def iter_mem(chunk_size: int = 1024 * 256) -> Iterator[bytes]:
            offset = 0
            while offset < total:
                nxt = min(offset + chunk_size, total)
                yield blob[offset:nxt]
                offset = nxt

        return StreamingResponse(
            iter_mem(),
            status_code=200,
            headers={
                "Content-Type": media_type,
                "Content-Length": str(total),
                "Accept-Ranges": "bytes",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Access-Control-Allow-Origin": "*",
            },
        )
    except Exception:
        # Fall back to URL streaming when SDK download is unavailable
        pass

    # Short-lived URL; avoid response overrides here to keep compatibility
    url = sp.get_file_url(object_key, expires_in=300)

    # Build request with optional Range header
    req = urllib.request.Request(url)
    if range_header:
        req.add_header("Range", range_header)

    try:
        resp = urllib.request.urlopen(req)  # nosec - controlled URL
    except HTTPError as e:
        # Pass through 404/416, etc.
        raise HTTPException(status_code=e.code, detail=str(e)) from e

    status = resp.getcode() or 200
    headers = resp.info()
    content_length = headers.get("Content-Length")
    content_range = headers.get("Content-Range")

    def iter_stream(chunk_size: int = 1024 * 256) -> Iterator[bytes]:
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            yield chunk

    out_headers = {
        "Content-Type": media_type,
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Access-Control-Allow-Origin": "*",
    }
    if content_length:
        out_headers["Content-Length"] = content_length
    if content_range:
        out_headers["Content-Range"] = content_range
        out_headers["Accept-Ranges"] = "bytes"

    return StreamingResponse(iter_stream(), status_code=status, headers=out_headers)


## Preview endpoints moved to routes/preview.py


@router.get("/video/{file_id}")
async def get_video(_file_id: str, _request: Request) -> Any:
    """Removed legacy file-based endpoint."""
    raise HTTPException(status_code=410, detail="Use /api/tasks/{task_id}/video")


@router.get("/tasks/{task_id}/video")
async def get_video_by_task(task_id: str, request: Request) -> Any:
    """Serve video resolved by task_id (maps to file_id), range-capable.

    - Local: serve file (with optional Range) from `OUTPUT_DIR`.
    - Cloud:
      - If `PROXY_CLOUD_MEDIA=true`, proxy bytes (supports Range) to avoid CORS.
      - Otherwise, redirect (307) to a short-lived signed URL (no response overrides).
    """
    sp: StorageProvider = get_storage_provider()

    # Resolve the object key to serve
    object_key: str | None = None
    if sp.file_exists(f"{task_id}.mp4"):
        object_key = f"{task_id}.mp4"
    else:
        file_id = await _file_id_from_task(task_id)
        preferred_key = f"{file_id}.mp4"
        legacy_key = f"{file_id}_final.mp4"
        if sp.file_exists(preferred_key):
            object_key = preferred_key
        elif sp.file_exists(legacy_key):
            object_key = legacy_key

    if not object_key:
        raise HTTPException(status_code=404, detail="Video not found")

    media_type = "video/mp4"
    range_header = request.headers.get("range") or request.headers.get("Range")

    # Local filesystem serving
    if config.storage_provider == "local":
        actual_file_path = config.output_dir / object_key
        try:
            file_size = actual_file_path.stat().st_size
        except Exception as e:
            raise HTTPException(status_code=404, detail="Video not found") from e

        if range_header:
            # Parse Range: bytes=start-end
            try:
                units, _, rng = range_header.partition("=")
                start_s, _, end_s = rng.partition("-")
                if units.strip().lower() != "bytes":
                    raise ValueError("Unsupported range unit")
                start = int(start_s) if start_s else 0
                end = int(end_s) if end_s else file_size - 1
                start = max(0, start)
                end = min(end, file_size - 1)
                length = end - start + 1
            except Exception:
                # Malformed; ignore range
                start = 0
                end = file_size - 1
                length = file_size

            def iter_file(
                path: str, offset: int, length: int, chunk: int = 1024 * 256
            ) -> Iterator[bytes]:
                with open(path, "rb") as f:
                    f.seek(offset)
                    remaining = length
                    while remaining > 0:
                        data = f.read(min(chunk, remaining))
                        if not data:
                            break
                        remaining -= len(data)
                        yield data

            headers = {
                "Content-Type": media_type,
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(length),
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": f"inline; filename=presentation_{task_id}.mp4",
            }
            return StreamingResponse(
                iter_file(str(actual_file_path), start, length),
                status_code=206,
                headers=headers,
            )
        else:
            # No range: send entire file
            return FileResponse(
                str(actual_file_path),
                media_type=media_type,
                filename=f"presentation_{task_id}.mp4",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Cache-Control": "public, max-age=3600",
                    "Accept-Ranges": "bytes",
                    "Content-Disposition": f"inline; filename=presentation_{task_id}.mp4",
                },
            )

    # Cloud storage
    if config.proxy_cloud_media:
        # Proxy through API for CORS-safe range streaming
        return await _proxy_cloud_media(object_key, media_type, range_header)

    # Redirect to signed URL (no response overrides to keep range-friendly)
    url = sp.get_file_url(object_key, expires_in=300)
    return Response(
        status_code=307,
        headers={
            "Location": url,
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/tasks/{task_id}/video/download")
async def download_video_by_task(task_id: str) -> Any:
    """Provide a download-focused endpoint for video with attachment disposition."""
    sp: StorageProvider = get_storage_provider()
    # Prefer task-id-based filename when present
    object_key = f"{task_id}.mp4" if sp.file_exists(f"{task_id}.mp4") else None
    if object_key is None:
        file_id = await _file_id_from_task(task_id)
        # Fallback to file-id naming (new first, then legacy)
        preferred_key = f"{file_id}.mp4"
        legacy_key = f"{file_id}_final.mp4"
        object_key = preferred_key if sp.file_exists(preferred_key) else legacy_key

    if not sp.file_exists(object_key):
        raise HTTPException(status_code=404, detail="Video not found")

    # Local: serve file directly with attachment headers
    if config.storage_provider == "local":
        actual_file_path = config.output_dir / object_key
        return FileResponse(
            str(actual_file_path),
            media_type="video/mp4",
            filename=f"presentation_{task_id}.mp4",
            headers={
                "Content-Disposition": f"attachment; filename=presentation_{task_id}.mp4",
                "Access-Control-Allow-Origin": "*",
            },
        )

    # Cloud: redirect to presigned URL with attachment disposition
    url = sp.get_file_url(
        object_key,
        expires_in=600,
        content_disposition=f"attachment; filename=presentation_{task_id}.mp4",
        content_type="video/mp4",
    )
    return Response(
        status_code=307,
        headers={
            "Location": url,
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.options("/tasks/{task_id}/video")
async def options_video_by_task(task_id: str) -> Response:
    """OPTIONS endpoint for task-based video (CORS preflight)."""
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language, Content-Type",
        "Access-Control-Max-Age": "600",
    }
    return Response(status_code=204, headers=headers)


@router.head("/tasks/{task_id}/video")
async def head_video_by_task(task_id: str) -> Response:
    """HEAD endpoint to check if the generated video exists (task-based)."""
    sp: StorageProvider = get_storage_provider()
    # Determine existence using task-id-based or file-id-based key
    exists = False
    if sp.file_exists(f"{task_id}.mp4"):
        exists = True
    else:
        try:
            file_id = await _file_id_from_task(task_id)
            if sp.file_exists(f"{file_id}.mp4") or sp.file_exists(
                f"{file_id}_final.mp4"
            ):
                exists = True
        except Exception:
            exists = False

    headers = {
        "Content-Type": "video/mp4",
        "Accept-Ranges": "bytes",
        "Content-Disposition": f"inline; filename=presentation_{task_id}.mp4",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language, Content-Type",
        "Cache-Control": "public, max-age=3600",
    }
    return Response(status_code=200 if exists else 404, headers=headers)


@router.get("/audio/{file_id}/tracks")
async def list_audio_files(file_id: str) -> dict[str, Any]:
    """Return a list of generated audio tracks for the given file."""
    from slidespeaker.core.state_manager import state_manager as sm

    state = await sm.get_state(file_id)
    if not state:
        raise HTTPException(status_code=404, detail="State not found")

    audio_files = await _get_audio_files_from_state(file_id)
    # Get file extension to determine step key and labels
    file_ext = (state.get("file_ext") or "").lower()
    label = "Chapter" if file_ext == ".pdf" else "Slide"
    # Attempt to read storage URLs from state for convenience
    storage_urls: list[str] = []
    step_key = "generate_pdf_audio" if file_ext == ".pdf" else "generate_audio"
    step = (state.get("steps") or {}).get(step_key) or {}
    if isinstance(step.get("storage_urls"), list):
        storage_urls = step["storage_urls"]

    tracks: list[dict[str, Any]] = []
    for i, path in enumerate(audio_files):
        tracks.append(
            {
                "index": i + 1,
                "name": f"{label} {i + 1}",
                "api_url": f"/api/audio/{file_id}/{i + 1}",
                "path": path,
                "storage_url": storage_urls[i] if i < len(storage_urls) else None,
            }
        )

    return {
        "file_id": file_id,
        "language": state.get("voice_language", "english"),
        "count": len(tracks),
        "tracks": tracks,
    }


@router.get("/audio/{file_id}")
async def get_final_audio(file_id: str, request: Request) -> Any:
    """Serve a single final audio output for the whole presentation.

    Resolution order:
    1) If a final audio file exists in storage, serve/redirect it.
    2) If local storage and no final file, concatenate per-slide audio on the fly.
    3) Otherwise, fall back to serving the last generated audio track.
    """
    sp: StorageProvider = get_storage_provider()

    # 1) Prebuilt final audio in storage
    for key in _final_audio_object_keys(file_id):
        if config.storage_provider == "local":
            # Local FS: verify and serve directly
            actual = config.output_dir / key
            try:
                if actual.exists() and actual.is_file():
                    return FileResponse(
                        str(actual),
                        media_type="audio/mpeg",
                        filename=f"presentation_{file_id}.mp3",
                        headers={
                            "Access-Control-Allow-Origin": "*",
                            "Cache-Control": "public, max-age=3600",
                            "Content-Disposition": f"inline; filename=presentation_{file_id}.mp3",
                        },
                    )
            except Exception:
                pass
        else:
            # Cloud: try proxying the object key without relying on HEAD permissions
            try:
                if config.proxy_cloud_media:
                    return await _proxy_cloud_media(key, "audio/mpeg", None)
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
        audio_files = await _get_audio_files_from_state(file_id)
        if audio_files:
            return StreamingResponse(
                _stream_concatenated_files(audio_files),
                media_type="audio/mpeg",
                headers={
                    # Serve inline so <audio> can play concatenated bytes
                    "Content-Disposition": f"inline; filename=presentation_{file_id}.mp3",
                    "Access-Control-Allow-Origin": "*",
                    "Cache-Control": "no-cache",
                },
            )

    # 3) Fallback: last generated track (serve inline)
    audio_files = await _get_audio_files_from_state(file_id)
    if not audio_files:
        raise HTTPException(status_code=404, detail="Final audio not found")
    try:
        actual_file_path = audio_files[-1]
        return FileResponse(
            actual_file_path,
            media_type="audio/mpeg",
            filename=f"presentation_{file_id}.mp3",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": f"inline; filename=presentation_{file_id}.mp3",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail="Final audio not found") from e


@router.get("/tasks/{task_id}/audio/tracks")
async def list_audio_files_by_task(task_id: str) -> dict[str, Any]:
    """List audio tracks using task_id and emit task-based URLs."""
    file_id = await _file_id_from_task(task_id)
    data = await list_audio_files(file_id)
    # Override api_url to task-based path for each track
    for t in data.get("tracks", []):
        idx = t.get("index")
        t["api_url"] = f"/api/tasks/{task_id}/audio/{idx}"
    data["task_id"] = task_id
    return data


@router.get("/tasks/{task_id}/audio")
async def get_final_audio_by_task(task_id: str, request: Request) -> Any:
    """Serve final audio by task, preferring task-id-based object keys.

    Avoid pre-checks that can fail on cloud providers with restricted HEAD permissions.
    Try task-id first; on 404, fall back to file-id mapping.
    """
    file_id = await _file_id_from_task(task_id)
    try:
        return await get_final_audio(task_id, request)
    except HTTPException as e:
        if e.status_code != 404:
            raise
        return await get_final_audio(file_id, request)


@router.get("/tasks/{task_id}/audio/download")
async def download_final_audio_by_task(task_id: str) -> Any:
    """Download endpoint for the final MP3 with attachment disposition."""
    sp: StorageProvider = get_storage_provider()
    # Resolve best key (prefer task-id, then file-id variants)
    if sp.file_exists(f"{task_id}.mp3"):
        object_key = f"{task_id}.mp3"
    else:
        file_id = await _file_id_from_task(task_id)
        keys = _final_audio_object_keys(file_id)
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


@router.get("/audio/{file_id}/{index}")
async def get_audio_file(file_id: str, index: int) -> Any:
    raise HTTPException(status_code=410, detail="Use task-based endpoints")


@router.get("/tasks/{task_id}/audio/{index}")
async def get_audio_file_by_task(task_id: str, index: int) -> Any:
    """Serve a single generated audio track by 1-based index (task-based)."""
    file_id = await _file_id_from_task(task_id)
    audio_files = await _get_audio_files_from_state(file_id)
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


"""All file-id routes removed. Use task-based endpoints."""


"""File-id SRT route removed."""


"""File-id VTT route removed."""


@router.get("/tasks/{task_id}/subtitles/srt")
async def get_srt_subtitles_by_task(
    task_id: str, language: str | None = None
) -> Response:
    # Resolve file_id first to read state/language when needed
    file_id = await _file_id_from_task(task_id)
    from slidespeaker.configs.locales import locale_utils
    from slidespeaker.core.state_manager import state_manager

    sp: StorageProvider = get_storage_provider()

    # Determine language/locale
    subtitle_language = language
    if not subtitle_language:
        state = await state_manager.get_state(file_id)
        subtitle_language = (
            state["subtitle_language"]
            if state and state.get("subtitle_language")
            else "english"
        )
    locale_code = locale_utils.get_locale_code(subtitle_language)

    # Prefer task-id-based filename first
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

    # Fallback: file-id-based storage resolution
    possible = [
        f"{file_id}_{locale_code}.srt",
        f"{file_id}_final_{locale_code}.srt",
        f"{file_id}_final.srt",
    ]
    object_key = next((k for k in possible if sp.file_exists(k)), None)
    if object_key:
        subtitle_content = sp.download_bytes(object_key)
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
    # Fallback 2: local state paths if upload missing
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
    file_id = await _file_id_from_task(task_id)
    from slidespeaker.configs.locales import locale_utils
    from slidespeaker.core.state_manager import state_manager

    sp: StorageProvider = get_storage_provider()

    # Determine locale
    subtitle_language = language
    if not subtitle_language:
        st = await state_manager.get_state(file_id)
        if st and st.get("subtitle_language"):
            subtitle_language = st["subtitle_language"]
        elif st and st.get("voice_language"):
            subtitle_language = st["voice_language"]
        else:
            subtitle_language = "english"
    locale_code = locale_utils.get_locale_code(subtitle_language)

    # Resolve object_key (prefer task-id naming)
    possible = [
        f"{task_id}_{locale_code}.srt",
        f"{file_id}_{locale_code}.srt",
        f"{file_id}_final_{locale_code}.srt",
        f"{file_id}_final.srt",
    ]
    object_key = next((k for k in possible if sp.file_exists(k)), None)
    if not object_key:
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
    # Resolve file_id first to read state/language when needed
    file_id = await _file_id_from_task(task_id)
    from slidespeaker.configs.locales import locale_utils
    from slidespeaker.core.state_manager import state_manager

    sp: StorageProvider = get_storage_provider()

    # Determine language/locale
    subtitle_language = language
    if not subtitle_language:
        state = await state_manager.get_state(file_id)
        subtitle_language = (
            state["subtitle_language"]
            if state and state.get("subtitle_language")
            else "english"
        )
    locale_code = locale_utils.get_locale_code(subtitle_language)

    # Prefer task-id-based filename first
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

    # Fallback: file-id-based storage resolution
    possible = [
        f"{file_id}_{locale_code}.vtt",
        f"{file_id}_final_{locale_code}.vtt",
        f"{file_id}_final.vtt",
    ]
    object_key = next((k for k in possible if sp.file_exists(k)), None)
    if object_key:
        subtitle_content = sp.download_bytes(object_key)
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
    # Fallback 2: local state paths if upload missing
    from slidespeaker.core.state_manager import state_manager

    st2 = await state_manager.get_state(file_id)
    if st2 and "steps" in st2 and st2["steps"].get("generate_subtitles"):
        data = st2["steps"]["generate_subtitles"].get("data") or {}
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
    file_id = await _file_id_from_task(task_id)
    from slidespeaker.configs.locales import locale_utils
    from slidespeaker.core.state_manager import state_manager

    sp: StorageProvider = get_storage_provider()

    # Determine locale
    subtitle_language = language
    if not subtitle_language:
        st = await state_manager.get_state(file_id)
        if st and st.get("subtitle_language"):
            subtitle_language = st["subtitle_language"]
        elif st and st.get("voice_language"):
            subtitle_language = st["voice_language"]
        else:
            subtitle_language = "english"
    locale_code = locale_utils.get_locale_code(subtitle_language)

    # Resolve object_key (prefer task-id naming)
    possible = [
        f"{task_id}_{locale_code}.vtt",
        f"{file_id}_{locale_code}.vtt",
        f"{file_id}_final_{locale_code}.vtt",
        f"{file_id}_final.vtt",
    ]
    object_key = next((k for k in possible if sp.file_exists(k)), None)
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


"""File-id VTT OPTIONS removed."""


@router.options("/tasks/{task_id}/subtitles/vtt")
async def options_vtt_subtitles_by_task(task_id: str) -> Response:
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language, Content-Type",
        "Access-Control-Max-Age": "86400",
    }
    return Response(status_code=200, headers=headers)


"""File-id VTT HEAD removed."""


@router.head("/tasks/{task_id}/subtitles/vtt")
async def head_vtt_subtitles_by_task(
    task_id: str, language: str | None = None
) -> Response:
    from slidespeaker.configs.locales import locale_utils

    sp: StorageProvider = get_storage_provider()
    # Determine locale strictly from param (no file-id fallback)
    subtitle_language = language or "english"
    locale_code = locale_utils.get_locale_code(subtitle_language)
    # Check existence by task or file fallback
    file_id = await _file_id_from_task(task_id)
    possible = [
        f"{task_id}_{locale_code}.vtt",
        f"{file_id}_{locale_code}.vtt",
        f"{file_id}_final_{locale_code}.vtt",
        f"{file_id}_final.vtt",
    ]
    exists = any(sp.file_exists(k) for k in possible)
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


"""File-id SRT HEAD removed."""


@router.head("/tasks/{task_id}/subtitles/srt")
async def head_srt_subtitles_by_task(
    task_id: str, language: str | None = None
) -> Response:
    from slidespeaker.configs.locales import locale_utils

    sp: StorageProvider = get_storage_provider()
    subtitle_language = language or "english"
    locale_code = locale_utils.get_locale_code(subtitle_language)
    file_id = await _file_id_from_task(task_id)
    possible = [
        f"{task_id}_{locale_code}.srt",
        f"{file_id}_{locale_code}.srt",
        f"{file_id}_final_{locale_code}.srt",
        f"{file_id}_final.srt",
    ]
    exists = any(sp.file_exists(k) for k in possible)
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
