"""
Podcast download routes for serving generated podcast files.

This module provides API endpoints for downloading and streaming generated
podcast files with appropriate content types and headers.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse

from slidespeaker.auth import require_authenticated_user
from slidespeaker.configs.config import config, get_storage_provider
from slidespeaker.storage import StorageProvider

from .download_utils import file_id_from_task, proxy_cloud_media

router = APIRouter(
    prefix="/api",
    tags=["podcast_downloads"],
    dependencies=[Depends(require_authenticated_user)],
)


@router.get("/tasks/{task_id}/podcast")
async def get_podcast_by_task(task_id: str, request: Request) -> Any:
    """Serve podcast file for a task."""
    sp: StorageProvider = get_storage_provider()
    file_id = await file_id_from_task(task_id)

    # Prefer task-id.mp3 (new scheme), then fallback to legacy *_podcast.mp3
    candidate_keys = [
        f"{task_id}.mp3",
        f"{file_id}.mp3",
        f"{task_id}_podcast.mp3",
        f"{file_id}_podcast.mp3",
    ]

    # Try candidates without relying on provider-specific exists checks
    for object_key in candidate_keys:
        try:
            if config.storage_provider == "local":
                actual = config.output_dir / object_key
                if actual.exists():
                    return FileResponse(
                        str(actual),
                        media_type="audio/mpeg",
                        filename=f"podcast_{task_id}.mp3",
                        headers={
                            "Access-Control-Allow-Origin": "*",
                            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                            "Cache-Control": "public, max-age=3600",
                            "Content-Disposition": f"inline; filename=podcast_{task_id}.mp3",
                        },
                    )
                # Try next key
                continue

            # Cloud
            if config.proxy_cloud_media:
                range_header = request.headers.get("Range")
                return await proxy_cloud_media(object_key, "audio/mpeg", range_header)

            url = sp.get_file_url(
                object_key,
                expires_in=300,
                content_disposition=f"inline; filename=podcast_{task_id}.mp3",
                content_type="audio/mpeg",
            )
            return Response(
                status_code=307,
                headers={"Location": url, "Access-Control-Allow-Origin": "*"},
            )
        except HTTPException as e:
            # Try next candidate on 4xx
            if e.status_code in (400, 403, 404, 416):
                continue
            raise
        except Exception:
            # Try next candidate
            continue
    raise HTTPException(status_code=404, detail="Podcast not found")


@router.get("/tasks/{task_id}/podcast/download")
async def download_podcast_by_task(task_id: str) -> Any:
    """Download podcast file for a task."""
    sp: StorageProvider = get_storage_provider()

    # Prefer task-id.mp3, then file-id.mp3, then legacy *_podcast.mp3 variants
    priorities: list[str] = [
        f"{task_id}.mp3",
        "",  # will be replaced with file_id.mp3 after resolving file_id
        f"{task_id}_podcast.mp3",
        "",  # will be replaced with file_id_podcast.mp3
    ]
    object_key = None

    # Check task-id-first
    if priorities[0] and sp.file_exists(priorities[0]):
        object_key = priorities[0]
    if object_key is None:
        file_id = await file_id_from_task(task_id)
        priorities[1] = f"{file_id}.mp3"
        priorities[3] = f"{file_id}_podcast.mp3"
        for k in priorities[1:]:
            if k and sp.file_exists(k):
                object_key = k
                break
    if object_key is None:
        raise HTTPException(status_code=404, detail="Podcast not found")

    if config.storage_provider == "local":
        actual = config.output_dir / object_key
        return FileResponse(
            str(actual),
            media_type="audio/mpeg",
            filename=f"podcast_{task_id}.mp3",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Content-Disposition": f"attachment; filename=podcast_{task_id}.mp3",
            },
        )

    url = sp.get_file_url(
        object_key,
        expires_in=600,
        content_disposition=f"attachment; filename=podcast_{task_id}.mp3",
        content_type="audio/mpeg",
    )
    return Response(
        status_code=307, headers={"Location": url, "Access-Control-Allow-Origin": "*"}
    )
