"""
Video download routes for serving generated presentation videos.

This module provides API endpoints for downloading and streaming generated
presentation videos with appropriate content types and headers.
"""

from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse

from slidespeaker.configs.config import config, get_storage_provider
from slidespeaker.storage import StorageProvider

from .download_utils import file_id_from_task, proxy_cloud_media

router = APIRouter(prefix="/api", tags=["video_downloads"])


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
        file_id = await file_id_from_task(task_id)
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
        return await proxy_cloud_media(object_key, media_type, range_header)

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
        file_id = await file_id_from_task(task_id)
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
            file_id = await file_id_from_task(task_id)
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
