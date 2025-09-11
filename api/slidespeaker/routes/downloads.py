"""
Download routes for serving generated files.

This module provides API endpoints for downloading generated presentation videos
and subtitle files. It handles file serving with appropriate content types and headers.
"""

from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse

from slidespeaker.storage import StorageProvider
from slidespeaker.utils.config import config, get_storage_provider
from slidespeaker.video import VideoPreviewer

router = APIRouter(prefix="/api", tags=["downloads"])

# Initialize video previewer
video_previewer = VideoPreviewer()


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
    from slidespeaker.core.task_queue import task_queue
    from slidespeaker.utils.redis_config import RedisConfig

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


@router.get("/preview/{file_id}")
async def get_video_preview(file_id: str, language: str = "english") -> dict[str, Any]:
    """Get video preview data including video URL and subtitle information."""
    try:
        preview_data = video_previewer.generate_preview_data(file_id, language)
        return preview_data
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate preview: {str(e)}"
        ) from e


@router.get("/video/{file_id}")
async def get_video(file_id: str, request: Request) -> Any:
    """Serve generated video file with HTTP Range support for HTML5 video."""
    sp: StorageProvider = get_storage_provider()
    preferred_key = f"{file_id}.mp4"
    legacy_key = f"{file_id}_final.mp4"
    object_key = (
        preferred_key
        if get_storage_provider().file_exists(preferred_key)
        else legacy_key
    )
    # Check if file exists
    if not sp.file_exists(object_key):
        raise HTTPException(status_code=404, detail="Video not found")

    range_header = request.headers.get("range") or request.headers.get("Range")

    # Get the file URL from storage provider (works for all storage types)
    file_url = sp.get_file_url(object_key, expires_in=300)

    # Log the generated URL for debugging (first 100 chars)
    print(f"DEBUG: Generated file URL for video: {file_url[:100]}...")

    # Handle range requests based on storage provider
    if range_header:
        if config.storage_provider == "local":
            # For local storage, serve directly with range support using the actual file path
            # FastAPI's FileResponse handles range requests automatically
            # Get the actual file path for local storage
            actual_file_path = config.output_dir / object_key
            print(
                f"DEBUG: Serving range request directly from local file: {actual_file_path}"
            )
            return FileResponse(
                str(actual_file_path),  # Use the actual file path from storage
                media_type="video/mp4",
                filename=f"presentation_{file_id}.mp4",
                headers={
                    "Content-Disposition": f"inline; filename=presentation_{file_id}.mp4",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                    "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Accept-Ranges": "bytes",
                },
            )
        else:
            # For cloud storage, redirect to presigned URL
            print(
                f"DEBUG: Redirecting range request to storage URL: {file_url[:100]}..."
            )
            return Response(
                status_code=307,
                headers={
                    "Location": file_url,
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                    "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language",
                },
            )

    # For non-range requests, handle based on storage provider
    if config.storage_provider == "local":
        # Local storage: serve directly for better performance using the actual file path
        # Get the actual file path for local storage
        actual_file_path = config.output_dir / object_key
        print(
            f"DEBUG: Serving non-range request directly from local file: {actual_file_path}"
        )
        return FileResponse(
            str(actual_file_path),  # Use the actual file path from storage
            media_type="video/mp4",
            filename=f"presentation_{file_id}.mp4",
            headers={
                "Content-Disposition": f"inline; filename=presentation_{file_id}.mp4",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Cache-Control": "public, max-age=3600",
                "Accept-Ranges": "bytes",
            },
        )
    else:
        # Cloud storage: redirect to presigned URL for non-range requests too
        print(
            f"DEBUG: Redirecting non-range request to storage URL: {file_url[:100]}..."
        )
        return Response(
            status_code=307,
            headers={
                "Location": file_url,
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language",
            },
        )


@router.get("/tasks/{task_id}/video")
async def get_video_by_task(task_id: str, request: Request) -> Any:
    """Serve video resolved by task_id (maps to file_id)."""
    sp: StorageProvider = get_storage_provider()
    # If we have migrated to task-id-based filenames, serve those directly
    if sp.file_exists(f"{task_id}.mp4"):
        return await get_video(task_id, request)
    # Otherwise resolve to file_id and serve legacy/file-id-based names
    file_id = await _file_id_from_task(task_id)
    return await get_video(file_id, request)


@router.options("/tasks/{task_id}/video")
async def options_video_by_task(task_id: str) -> Response:
    """OPTIONS endpoint for task-based video (CORS preflight)."""
    return await options_video("dummy")


@router.head("/tasks/{task_id}/video")
async def head_video_by_task(task_id: str) -> Response:
    """HEAD endpoint to check if the generated video exists (task-based)."""
    sp: StorageProvider = get_storage_provider()
    # Prefer task-id-based filename when present
    if sp.file_exists(f"{task_id}.mp4"):
        headers = {
            "Content-Type": "video/mp4",
            "Accept-Ranges": "bytes",
            "Content-Disposition": f"inline; filename=presentation_{task_id}.mp4",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language, Content-Type",
            "Cache-Control": "public, max-age=3600",
        }
        return Response(status_code=200, headers=headers)
    # Otherwise, resolve to file_id and reuse file-based HEAD logic
    file_id = await _file_id_from_task(task_id)
    return await head_video(file_id)


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
        if sp.file_exists(key):
            if config.storage_provider == "local":
                actual = config.output_dir / key
                return FileResponse(
                    str(actual),
                    media_type="audio/mpeg",
                    filename=f"presentation_{file_id}.mp3",
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Cache-Control": "public, max-age=3600",
                    },
                )
            else:
                url = sp.get_file_url(key, expires_in=300)
                return Response(
                    status_code=307,
                    headers={
                        "Location": url,
                        "Cache-Control": "no-cache, no-store, must-revalidate",
                        "Access-Control-Allow-Origin": "*",
                    },
                )

    # 2) Local: concatenate audio files
    if config.storage_provider == "local":
        audio_files = await _get_audio_files_from_state(file_id)
        if audio_files:
            return StreamingResponse(
                _stream_concatenated_files(audio_files),
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": f"attachment; filename=presentation_{file_id}.mp3",
                    "Access-Control-Allow-Origin": "*",
                    "Cache-Control": "no-cache",
                },
            )

    # 3) Fallback: last generated track
    audio_files = await _get_audio_files_from_state(file_id)
    if not audio_files:
        raise HTTPException(status_code=404, detail="Final audio not found")
    return await get_audio_file(file_id, len(audio_files))


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
    file_id = await _file_id_from_task(task_id)
    sp: StorageProvider = get_storage_provider()
    if sp.file_exists(f"{task_id}.mp3"):
        return await get_final_audio(task_id, request)
    return await get_final_audio(file_id, request)


@router.get("/audio/{file_id}/{index}")
async def get_audio_file(file_id: str, index: int) -> Any:
    """Serve a single generated audio track by 1-based index."""
    audio_files = await _get_audio_files_from_state(file_id)
    if not audio_files:
        raise HTTPException(status_code=404, detail="Audio not found")
    if index < 1 or index > len(audio_files):
        raise HTTPException(status_code=404, detail="Audio index out of range")

    actual_file_path = audio_files[index - 1]
    return FileResponse(
        actual_file_path,
        media_type="audio/mpeg",
        filename=f"{file_id}_track_{index}.mp3",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Cache-Control": "public, max-age=3600",
        },
    )


@router.get("/tasks/{task_id}/audio/{index}")
async def get_audio_file_by_task(task_id: str, index: int) -> Any:
    file_id = await _file_id_from_task(task_id)
    return await get_audio_file(file_id, index)


@router.options("/video/{file_id}")
async def options_video(file_id: str) -> Response:
    """OPTIONS endpoint to handle CORS preflight requests for video."""
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language, Content-Type",
        "Access-Control-Max-Age": "86400",
    }
    return Response(status_code=200, headers=headers)


@router.head("/video/{file_id}")
async def head_video(file_id: str) -> Response:
    """HEAD endpoint to check if the generated video exists."""
    sp: StorageProvider = get_storage_provider()
    object_key = (
        f"{file_id}.mp4" if sp.file_exists(f"{file_id}.mp4") else f"{file_id}_final.mp4"
    )
    if not sp.file_exists(object_key):
        raise HTTPException(status_code=404, detail="Video not found")

    # For cloud storage, we can't easily get file size without downloading metadata
    # So we'll use a generic response
    headers = {
        "Content-Type": "video/mp4",
        "Accept-Ranges": "bytes",
        "Content-Disposition": f"inline; filename=presentation_{file_id}.mp4",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language, Content-Type",
        "Cache-Control": "public, max-age=3600",
    }
    return Response(status_code=200, headers=headers)


@router.options("/subtitles/{file_id}/srt")
async def options_srt_subtitles(file_id: str) -> Response:
    """OPTIONS endpoint to handle CORS preflight requests for SRT subtitles."""
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language, Content-Type",
        "Access-Control-Max-Age": "86400",
    }
    return Response(status_code=200, headers=headers)


@router.get("/subtitles/{file_id}/srt")
async def get_srt_subtitles(file_id: str, language: str | None = None) -> Response:
    """Download SRT subtitle file."""
    # Get the subtitle language from query parameter or file's state
    from slidespeaker.core.state_manager import state_manager

    # Use query parameter if provided; normalize input
    subtitle_language = language
    if not subtitle_language:
        # If no language specified, get from file state
        state = await state_manager.get_state(file_id)
        if state and "subtitle_language" in state and state["subtitle_language"]:
            subtitle_language = state["subtitle_language"]
        elif state and "voice_language" in state:
            subtitle_language = state["voice_language"]
        else:
            subtitle_language = "english"  # Default to English

    # Convert language to locale code (normalize first)
    from slidespeaker.utils.locales import locale_utils

    subtitle_language = locale_utils.normalize_language(subtitle_language)
    locale_code = locale_utils.get_locale_code(subtitle_language)

    # Try locale-aware filename first, then fall back to legacy format
    # Prefer new naming without _final, fallback to legacy
    object_key = f"{file_id}_{locale_code}.srt"

    # If the expected file doesn't exist, try to find what actually exists
    sp: StorageProvider = get_storage_provider()
    if not sp.file_exists(object_key):
        # Try other common locale codes that might exist
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
        found_file = False
        for locale in common_locales:
            test_key = f"{file_id}_{locale}.srt"
            if sp.file_exists(test_key):
                object_key = test_key
                found_file = True
                break

        # If still not found, try legacy format
        if not found_file:
            legacy_key = f"{file_id}_final_{locale_code}.srt"
            if sp.file_exists(legacy_key):
                object_key = legacy_key
            else:
                legacy2 = f"{file_id}_final.srt"
                if sp.file_exists(legacy2):
                    object_key = legacy2
                else:
                    raise HTTPException(
                        status_code=404, detail="SRT subtitles not found"
                    )

    # Download subtitle content
    subtitle_content = sp.download_bytes(object_key)

    # Optional diagnostics headers: language and source recorded by generator
    diag_headers = {}
    try:
        from slidespeaker.core.state_manager import state_manager as _sm

        st = await _sm.get_state(file_id)
        if isinstance(st, dict) and isinstance(st.get("subtitle_generation"), dict):
            sg = st["subtitle_generation"]
            if sg.get("language"):
                diag_headers["X-Subtitle-Language"] = str(sg["language"])
            if sg.get("source"):
                diag_headers["X-Subtitle-Source"] = str(sg["source"])
            if sg.get("pipeline"):
                diag_headers["X-Subtitle-Pipeline"] = str(sg["pipeline"])
    except Exception:
        pass

    return Response(
        content=subtitle_content,
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=presentation_{file_id}_{locale_code}.srt",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language, Content-Type",
            "Cache-Control": "public, max-age=3600",  # Add caching to prevent constant requests
            **diag_headers,
        },
    )


@router.get("/subtitles/{file_id}/vtt")
async def get_vtt_subtitles(file_id: str, language: str | None = None) -> Response:
    """Download VTT subtitle file."""
    # Get the subtitle language from query parameter or file's state
    from slidespeaker.core.state_manager import state_manager

    subtitle_language = language
    if not subtitle_language:
        # If no language specified, get from file state
        state = await state_manager.get_state(file_id)
        if state and "subtitle_language" in state and state["subtitle_language"]:
            subtitle_language = state["subtitle_language"]
        elif state and "voice_language" in state:
            subtitle_language = state["voice_language"]
        else:
            subtitle_language = "english"  # Default to English

    # Convert language to locale code
    from slidespeaker.utils.locales import locale_utils

    subtitle_language = locale_utils.normalize_language(subtitle_language)
    locale_code = locale_utils.get_locale_code(subtitle_language)

    # Try locale-aware filename first, then fall back to legacy format
    object_key = f"{file_id}_{locale_code}.vtt"

    # If the expected file doesn't exist, try to find what actually exists
    sp: StorageProvider = get_storage_provider()
    if not sp.file_exists(object_key):
        # Try other common locale codes that might exist
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
        found_file = False
        for locale in common_locales:
            test_key = f"{file_id}_{locale}.vtt"
            if sp.file_exists(test_key):
                object_key = test_key
                found_file = True
                break

        # If still not found, try legacy format
        if not found_file:
            legacy_key = f"{file_id}_final_{locale_code}.vtt"
            if sp.file_exists(legacy_key):
                object_key = legacy_key
            else:
                legacy2 = f"{file_id}_final.vtt"
                if sp.file_exists(legacy2):
                    object_key = legacy2
                else:
                    raise HTTPException(
                        status_code=404, detail="VTT subtitles not found"
                    )

    # Download subtitle content
    subtitle_content = sp.download_bytes(object_key)

    # Optional diagnostics headers: language and source recorded by generator
    diag_headers = {}
    try:
        from slidespeaker.core.state_manager import state_manager as _sm

        st = await _sm.get_state(file_id)
        if isinstance(st, dict) and isinstance(st.get("subtitle_generation"), dict):
            sg = st["subtitle_generation"]
            if sg.get("language"):
                diag_headers["X-Subtitle-Language"] = str(sg["language"])
            if sg.get("source"):
                diag_headers["X-Subtitle-Source"] = str(sg["source"])
            if sg.get("pipeline"):
                diag_headers["X-Subtitle-Pipeline"] = str(sg["pipeline"])
    except Exception:
        pass

    return Response(
        content=subtitle_content,
        media_type="text/vtt",
        headers={
            "Content-Disposition": f"inline; filename=presentation_{file_id}_{locale_code}.vtt",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language, Content-Type",
            "Cache-Control": "public, max-age=3600",  # Add caching to prevent constant requests
            **diag_headers,
        },
    )


@router.get("/tasks/{task_id}/subtitles/srt")
async def get_srt_subtitles_by_task(
    task_id: str, language: str | None = None
) -> Response:
    # Resolve file_id first to read state/language when needed
    file_id = await _file_id_from_task(task_id)
    from slidespeaker.core.state_manager import state_manager
    from slidespeaker.utils.locales import locale_utils

    sp: StorageProvider = get_storage_provider()

    # Determine language/locale
    subtitle_language = language
    if not subtitle_language:
        state = await state_manager.get_state(file_id)
        if state and state.get("subtitle_language"):
            subtitle_language = state["subtitle_language"]
        elif state and state.get("voice_language"):
            subtitle_language = state["voice_language"]
        else:
            subtitle_language = "english"
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

    # Fallback to file-id-based resolution and legacy
    return await get_srt_subtitles(file_id, subtitle_language)


@router.get("/tasks/{task_id}/subtitles/vtt")
async def get_vtt_subtitles_by_task(
    task_id: str, language: str | None = None
) -> Response:
    # Resolve file_id first to read state/language when needed
    file_id = await _file_id_from_task(task_id)
    from slidespeaker.core.state_manager import state_manager
    from slidespeaker.utils.locales import locale_utils

    sp: StorageProvider = get_storage_provider()

    # Determine language/locale
    subtitle_language = language
    if not subtitle_language:
        state = await state_manager.get_state(file_id)
        if state and state.get("subtitle_language"):
            subtitle_language = state["subtitle_language"]
        elif state and state.get("voice_language"):
            subtitle_language = state["voice_language"]
        else:
            subtitle_language = "english"
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

    # Fallback to file-id-based resolution and legacy
    return await get_vtt_subtitles(file_id, subtitle_language)


@router.options("/subtitles/{file_id}/vtt")
async def options_vtt_subtitles(file_id: str) -> Response:
    """OPTIONS endpoint to handle CORS preflight requests for VTT subtitles."""
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language, Content-Type",
        "Access-Control-Max-Age": "86400",
    }
    return Response(status_code=200, headers=headers)


@router.options("/tasks/{task_id}/subtitles/vtt")
async def options_vtt_subtitles_by_task(task_id: str) -> Response:
    return await options_vtt_subtitles("dummy")


@router.head("/subtitles/{file_id}/vtt")
async def head_vtt_subtitles(file_id: str, language: str | None = None) -> Response:
    """HEAD endpoint to check if VTT subtitle file exists."""
    # Get the subtitle language from query parameter or file's state
    from slidespeaker.core.state_manager import state_manager

    subtitle_language = language
    if not subtitle_language:
        # If no language specified, get from file state
        state = await state_manager.get_state(file_id)
        if state and "subtitle_language" in state and state["subtitle_language"]:
            subtitle_language = state["subtitle_language"]
        elif state and "voice_language" in state:
            subtitle_language = state["voice_language"]
        else:
            subtitle_language = "english"  # Default to English

    # Convert language to locale code
    from slidespeaker.utils.locales import locale_utils

    subtitle_language = locale_utils.normalize_language(subtitle_language)
    locale_code = locale_utils.get_locale_code(subtitle_language)

    # Try new locale-aware filename first, then fall back to legacy format
    object_key = f"{file_id}_{locale_code}.vtt"

    # If the expected file doesn't exist, try to find what actually exists
    sp: StorageProvider = get_storage_provider()
    if not sp.file_exists(object_key):
        # Try other common locale codes that might exist
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
        found_file = False
        for locale in common_locales:
            # Prefer new naming
            test_key = f"{file_id}_{locale}.vtt"
            if sp.file_exists(test_key):
                object_key = test_key
                found_file = True
                break

        # If still not found, try legacy format
        if not found_file:
            legacy_key = f"{file_id}_final.vtt"
            if sp.file_exists(legacy_key):
                object_key = legacy_key
            else:
                raise HTTPException(status_code=404, detail="VTT subtitles not found")

    headers = {
        "Content-Type": "text/vtt",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language, Content-Type",
        "Cache-Control": "public, max-age=3600",  # Add caching to prevent constant requests
    }
    return Response(status_code=200, headers=headers)


@router.head("/tasks/{task_id}/subtitles/vtt")
async def head_vtt_subtitles_by_task(
    task_id: str, language: str | None = None
) -> Response:
    # Prefer task-id-based filenames if present
    file_id = await _file_id_from_task(task_id)
    from slidespeaker.core.state_manager import state_manager
    from slidespeaker.utils.locales import locale_utils

    sp: StorageProvider = get_storage_provider()

    subtitle_language = language
    if not subtitle_language:
        state = await state_manager.get_state(file_id)
        if state and state.get("subtitle_language"):
            subtitle_language = state["subtitle_language"]
        elif state and state.get("voice_language"):
            subtitle_language = state["voice_language"]
        else:
            subtitle_language = "english"
    locale_code = locale_utils.get_locale_code(subtitle_language)
    if sp.file_exists(f"{task_id}_{locale_code}.vtt"):
        headers = {
            "Content-Type": "text/vtt",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language, Content-Type",
            "Cache-Control": "public, max-age=3600",
        }
        return Response(status_code=200, headers=headers)
    return await head_vtt_subtitles(file_id, subtitle_language)


@router.head("/subtitles/{file_id}/srt")
async def head_srt_subtitles(file_id: str, language: str | None = None) -> Response:
    """HEAD endpoint to check if SRT subtitle file exists."""
    # Get the subtitle language from query parameter or file's state
    from slidespeaker.core.state_manager import state_manager

    subtitle_language = language
    if not subtitle_language:
        # If no language specified, get from file state
        state = await state_manager.get_state(file_id)
        if state and "subtitle_language" in state and state["subtitle_language"]:
            subtitle_language = state["subtitle_language"]
        elif state and "voice_language" in state:
            subtitle_language = state["voice_language"]
        else:
            subtitle_language = "english"  # Default to English

    # Convert language to locale code
    from slidespeaker.utils.locales import locale_utils

    subtitle_language = locale_utils.normalize_language(subtitle_language)
    locale_code = locale_utils.get_locale_code(subtitle_language)

    # Try new locale-aware filename first, then fall back to legacy format
    object_key = f"{file_id}_{locale_code}.srt"

    # Get storage provider
    sp: StorageProvider = get_storage_provider()

    # If the expected file doesn't exist, try to find what actually exists
    if not sp.file_exists(object_key):
        # Try other common locale codes that might exist
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
        found_file = False
        for locale in common_locales:
            # Prefer new naming
            test_key = f"{file_id}_{locale}.srt"
            if sp.file_exists(test_key):
                object_key = test_key
                found_file = True
                break

        # If still not found, try legacy format
        if not found_file:
            legacy_key = f"{file_id}_final.srt"
            if sp.file_exists(legacy_key):
                object_key = legacy_key
            else:
                raise HTTPException(status_code=404, detail="SRT subtitles not found")

    headers = {
        "Content-Type": "text/plain",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language, Content-Type",
        "Cache-Control": "public, max-age=3600",  # Add caching to prevent constant requests
    }
    return Response(status_code=200, headers=headers)


@router.head("/tasks/{task_id}/subtitles/srt")
async def head_srt_subtitles_by_task(
    task_id: str, language: str | None = None
) -> Response:
    # Prefer task-id-based filenames if present
    file_id = await _file_id_from_task(task_id)
    from slidespeaker.core.state_manager import state_manager
    from slidespeaker.utils.locales import locale_utils

    sp: StorageProvider = get_storage_provider()

    subtitle_language = language
    if not subtitle_language:
        state = await state_manager.get_state(file_id)
        if state and state.get("subtitle_language"):
            subtitle_language = state["subtitle_language"]
        elif state and state.get("voice_language"):
            subtitle_language = state["voice_language"]
        else:
            subtitle_language = "english"
    locale_code = locale_utils.get_locale_code(subtitle_language)
    if sp.file_exists(f"{task_id}_{locale_code}.srt"):
        headers = {
            "Content-Type": "text/plain",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language, Content-Type",
            "Cache-Control": "public, max-age=3600",
        }
        return Response(status_code=200, headers=headers)
    return await head_srt_subtitles(file_id, subtitle_language)
