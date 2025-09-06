"""
Download routes for serving generated files.

This module provides API endpoints for downloading generated presentation videos
and subtitle files. It handles file serving with appropriate content types and headers.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse

from slidespeaker.processing.video_previewer import VideoPreviewer
from slidespeaker.storage import StorageProvider
from slidespeaker.utils.config import config, get_storage_provider

router = APIRouter(prefix="/api", tags=["downloads"])

# Get storage provider instance
storage_provider: StorageProvider = get_storage_provider()

# Initialize video previewer
video_previewer = VideoPreviewer()


@router.get("/video/{file_id}")
async def get_video(file_id: str, request: Request) -> Any:
    """Serve generated video file with HTTP Range support for HTML5 video."""
    object_key = f"{file_id}_final.mp4"

    # Check if file exists
    if not storage_provider.file_exists(object_key):
        raise HTTPException(status_code=404, detail="Video not found")

    range_header = request.headers.get("range") or request.headers.get("Range")

    # Get the file URL from storage provider (works for all storage types)
    file_url = storage_provider.get_file_url(object_key, expires_in=300)

    # Log the generated URL for debugging (first 100 chars)
    print(f"DEBUG: Generated file URL for video: {file_url[:100]}...")

    # Handle range requests based on storage provider
    if range_header:
        if config.storage_provider == "local":
            # For local storage, serve directly with range support using the actual file path
            # FastAPI's FileResponse handles range requests automatically
            print(f"DEBUG: Serving range request directly from local file: {file_url}")
            return FileResponse(
                file_url,  # Use the actual file path from storage
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
        print(f"DEBUG: Serving non-range request directly from local file: {file_url}")
        return FileResponse(
            file_url,  # Use the actual file path from storage
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
    object_key = f"{file_id}_final.mp4"
    if not storage_provider.file_exists(object_key):
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
async def get_srt_subtitles(file_id: str) -> Response:
    """Download SRT subtitle file."""
    # Try locale-aware filename first, then fall back to legacy format
    locale_code = "en"  # Default to English for now
    object_key = f"{file_id}_final_{locale_code}.srt"

    if not storage_provider.file_exists(object_key):
        # Fall back to legacy format for backward compatibility
        legacy_key = f"{file_id}_final.srt"
        if storage_provider.file_exists(legacy_key):
            object_key = legacy_key
        else:
            raise HTTPException(status_code=404, detail="SRT subtitles not found")

    # Download subtitle content
    subtitle_content = storage_provider.download_bytes(object_key)

    return Response(
        content=subtitle_content,
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=presentation_{file_id}.srt",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language, Content-Type",
        },
    )


@router.get("/subtitles/{file_id}/vtt")
async def get_vtt_subtitles(file_id: str) -> Response:
    """Download VTT subtitle file."""
    # Try locale-aware filename first, then fall back to legacy format
    locale_code = "en"  # Default to English for now
    object_key = f"{file_id}_final_{locale_code}.vtt"

    if not storage_provider.file_exists(object_key):
        # Fall back to legacy format for backward compatibility
        legacy_key = f"{file_id}_final.vtt"
        if storage_provider.file_exists(legacy_key):
            object_key = legacy_key
        else:
            raise HTTPException(status_code=404, detail="VTT subtitles not found")

    # Download subtitle content
    subtitle_content = storage_provider.download_bytes(object_key)

    return Response(
        content=subtitle_content,
        media_type="text/vtt",
        headers={
            "Content-Disposition": f"inline; filename=presentation_{file_id}.vtt",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language, Content-Type",
        },
    )


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


@router.head("/subtitles/{file_id}/vtt")
async def head_vtt_subtitles(file_id: str) -> Response:
    """HEAD endpoint to check if VTT subtitle file exists."""
    object_key = f"{file_id}_final.vtt"
    if not storage_provider.file_exists(object_key):
        raise HTTPException(status_code=404, detail="VTT subtitles not found")
    headers = {
        "Content-Type": "text/vtt",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language, Content-Type",
    }
    return Response(status_code=200, headers=headers)


@router.head("/subtitles/{file_id}/srt")
async def head_srt_subtitles(file_id: str) -> Response:
    """HEAD endpoint to check if SRT subtitle file exists."""
    object_key = f"{file_id}_final.srt"
    if not storage_provider.file_exists(object_key):
        raise HTTPException(status_code=404, detail="SRT subtitles not found")
    headers = {
        "Content-Type": "text/plain",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "Range, Accept, Accept-Encoding, Accept-Language, Content-Type",
    }
    return Response(status_code=200, headers=headers)
