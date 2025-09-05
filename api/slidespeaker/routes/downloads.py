"""
Download routes for serving generated files.

This module provides API endpoints for downloading generated presentation videos
and subtitle files. It handles file serving with appropriate content types and headers.
"""

import re
from collections.abc import Iterator

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse

from slidespeaker.utils.config import config

router = APIRouter(prefix="/api", tags=["downloads"])

OUTPUT_DIR = config.output_dir


@router.get("/video/{file_id}")
async def get_video(file_id: str, request: Request) -> StreamingResponse | FileResponse:
    """Serve generated video file with HTTP Range support for HTML5 video."""
    video_path = OUTPUT_DIR / f"{file_id}_final.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")

    file_size = video_path.stat().st_size
    range_header = request.headers.get("range") or request.headers.get("Range")

    # If the client requested a byte range, return 206 with partial content
    if range_header:
        # Expected format: bytes=start-end
        range_match = re.match(r"bytes=(\d+)-(\d*)", range_header)
        if range_match:
            start = int(range_match.group(1))
            end = range_match.group(2)
            end_byte = int(end) if end else file_size - 1

            if start >= file_size or end_byte >= file_size:
                # Invalid range
                raise HTTPException(
                    status_code=416, detail="Requested Range Not Satisfiable"
                )

            chunk_size = 1024 * 1024  # 1MB
            length = end_byte - start + 1

            def iter_file() -> Iterator[bytes]:
                with open(video_path, "rb") as f:
                    f.seek(start)
                    remaining = length
                    while remaining > 0:
                        read_size = min(chunk_size, remaining)
                        data = f.read(read_size)
                        if not data:
                            break
                        remaining -= len(data)
                        yield data

            headers = {
                "Content-Range": f"bytes {start}-{end_byte}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(length),
                "Content-Type": "video/mp4",
                "Content-Disposition": f"inline; filename=presentation_{file_id}.mp4",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Cache-Control": "public, max-age=3600",
            }
            return StreamingResponse(
                iter_file(), status_code=206, headers=headers, media_type="video/mp4"
            )

    # Fallback: serve whole file with Accept-Ranges header
    return FileResponse(
        video_path,
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


@router.head("/video/{file_id}")
async def head_video(file_id: str) -> Response:
    """HEAD endpoint to check if the generated video exists."""
    video_path = OUTPUT_DIR / f"{file_id}_final.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")

    headers = {
        "Content-Type": "video/mp4",
        "Content-Length": str(video_path.stat().st_size),
        "Accept-Ranges": "bytes",
        "Content-Disposition": f"inline; filename=presentation_{file_id}.mp4",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "*",
        "Cache-Control": "public, max-age=3600",
    }
    return Response(status_code=200, headers=headers)


@router.get("/subtitles/{file_id}/srt")
async def get_srt_subtitles(file_id: str) -> FileResponse:
    """Download SRT subtitle file."""
    srt_path = OUTPUT_DIR / f"{file_id}_final.srt"
    if not srt_path.exists():
        raise HTTPException(status_code=404, detail="SRT subtitles not found")

    return FileResponse(
        srt_path,
        media_type="text/plain",
        filename=f"presentation_{file_id}.srt",
        headers={
            "Content-Disposition": f"attachment; filename=presentation_{file_id}.srt",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


@router.get("/subtitles/{file_id}/vtt")
async def get_vtt_subtitles(file_id: str) -> FileResponse:
    """Download VTT subtitle file."""
    vtt_path = OUTPUT_DIR / f"{file_id}_final.vtt"
    if not vtt_path.exists():
        raise HTTPException(status_code=404, detail="VTT subtitles not found")

    return FileResponse(
        vtt_path,
        media_type="text/vtt",
        filename=f"presentation_{file_id}.vtt",
        headers={
            "Content-Disposition": f"inline; filename=presentation_{file_id}.vtt",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


@router.head("/subtitles/{file_id}/vtt")
async def head_vtt_subtitles(file_id: str) -> Response:
    """HEAD endpoint to check if VTT subtitle file exists."""
    vtt_path = OUTPUT_DIR / f"{file_id}_final.vtt"
    if not vtt_path.exists():
        raise HTTPException(status_code=404, detail="VTT subtitles not found")
    headers = {
        "Content-Type": "text/vtt",
        "Content-Length": str(vtt_path.stat().st_size),
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    }
    return Response(status_code=200, headers=headers)


@router.head("/subtitles/{file_id}/srt")
async def head_srt_subtitles(file_id: str) -> Response:
    """HEAD endpoint to check if SRT subtitle file exists."""
    srt_path = OUTPUT_DIR / f"{file_id}_final.srt"
    if not srt_path.exists():
        raise HTTPException(status_code=404, detail="SRT subtitles not found")
    headers = {
        "Content-Type": "text/plain",
        "Content-Length": str(srt_path.stat().st_size),
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    }
    return Response(status_code=200, headers=headers)
