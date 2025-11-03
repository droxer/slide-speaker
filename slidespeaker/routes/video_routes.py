"""
Video download routes for serving generated presentation videos.

This module provides API endpoints for downloading and streaming generated
presentation videos with appropriate content types and headers.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse

from slidespeaker.auth import require_authenticated_user
from slidespeaker.configs.config import config, get_storage_provider
from slidespeaker.storage import StorageProvider
from slidespeaker.storage.paths import output_object_key

from .download_helpers import (
    build_headers,
    check_file_exists,
    file_id_from_task,
    iter_file,
    proxy_cloud_media,
)

router = APIRouter(
    prefix="/api",
    tags=["video"],
    dependencies=[Depends(require_authenticated_user)],
)


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
    file_id = await file_id_from_task(task_id)
    candidate_keys = [
        output_object_key(task_id, "video", "final.mp4"),
        output_object_key(file_id, "video", "final.mp4"),
        f"{task_id}.mp4",
        f"{file_id}.mp4",
        f"{file_id}_final.mp4",
    ]
    object_key = next((k for k in candidate_keys if check_file_exists(k)), None)

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

            headers = build_headers(
                request,
                content_type=media_type,
                content_length=length,
                disposition=f"inline; filename=presentation_{task_id}.mp4",
            )
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
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
                headers=build_headers(
                    request,
                    content_type=media_type,
                    disposition=f"inline; filename=presentation_{task_id}.mp4",
                ),
            )

    # Cloud storage
    if config.proxy_cloud_media:
        # Proxy through API for CORS-safe range streaming
        origin = request.headers.get("origin") or request.headers.get("Origin")
        return await proxy_cloud_media(
            object_key, media_type, range_header, origin=origin
        )

    # Redirect to signed URL (no response overrides to keep range-friendly)
    url = sp.get_file_url(object_key, expires_in=300)
    headers = {"Location": url, "Cache-Control": "public, max-age=300, must-revalidate"}
    origin = request.headers.get("origin") or request.headers.get("Origin")
    if origin:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return Response(status_code=307, headers=headers)


@router.get("/tasks/{task_id}/video/download")
async def download_video_by_task(task_id: str, request: Request) -> Any:
    """Provide a download-focused endpoint for video with attachment disposition."""
    sp: StorageProvider = get_storage_provider()
    # Prefer task-id-based filename when present
    file_id = await file_id_from_task(task_id)
    candidate_keys = [
        output_object_key(task_id, "video", "final.mp4"),
        output_object_key(file_id, "video", "final.mp4"),
        f"{task_id}.mp4",
        f"{file_id}.mp4",
        f"{file_id}_final.mp4",
    ]
    object_key = next((k for k in candidate_keys if check_file_exists(k)), None)

    if not object_key:
        raise HTTPException(status_code=404, detail="Video not found")

    # Local: serve file directly with attachment headers
    if config.storage_provider == "local":
        actual_file_path = config.output_dir / object_key
        return FileResponse(
            str(actual_file_path),
            media_type="video/mp4",
            filename=f"presentation_{task_id}.mp4",
            headers=build_headers(
                request,
                content_type="video/mp4",
                disposition=f"attachment; filename=presentation_{task_id}.mp4",
            ),
        )

    # Cloud: redirect to presigned URL with attachment disposition
    # For OSS storage, avoid setting content_type to prevent header override errors
    get_file_url_kwargs = {
        "object_key": object_key,
        "expires_in": 600,
        "content_disposition": f"attachment; filename=presentation_{task_id}.mp4",
    }

    # Only set content_type for non-OSS providers
    if config.storage_provider != "oss":
        get_file_url_kwargs["content_type"] = "video/mp4"

    url = sp.get_file_url(**get_file_url_kwargs)
    headers = {"Location": url, "Cache-Control": "public, max-age-600, must-revalidate"}
    origin = request.headers.get("origin") or request.headers.get("Origin")
    if origin:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return Response(status_code=307, headers=headers)


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
async def head_video_by_task(task_id: str, request: Request) -> Response:
    """HEAD endpoint to check if the generated video exists (task-based)."""
    # Determine existence using task-id-based or file-id-based key
    try:
        file_id = await file_id_from_task(task_id)
    except Exception:
        file_id = task_id
    candidate_keys = [
        output_object_key(task_id, "video", "final.mp4"),
        output_object_key(file_id, "video", "final.mp4"),
        f"{task_id}.mp4",
        f"{file_id}.mp4",
        f"{file_id}_final.mp4",
    ]
    exists = any(check_file_exists(k) for k in candidate_keys)

    headers = build_headers(
        request,
        content_type="video/mp4",
        disposition=f"inline; filename=presentation_{task_id}.mp4",
    )
    headers["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS"
    headers["Access-Control-Allow-Headers"] = (
        "Range, Accept, Accept-Encoding, Accept-Language, Content-Type"
    )
    return Response(status_code=200 if exists else 404, headers=headers)
