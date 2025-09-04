"""Download routes for serving generated files."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from slidespeaker.utils.config import config

router = APIRouter(prefix="/api", tags=["downloads"])

OUTPUT_DIR = config.output_dir


@router.get("/video/{file_id}")
async def get_video(file_id: str) -> FileResponse:
    """Download the generated video file."""
    video_path = OUTPUT_DIR / f"{file_id}_final.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")

    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"presentation_{file_id}.mp4",
        headers={
            "Content-Disposition": f"attachment; filename=presentation_{file_id}.mp4"
        },
    )


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
            "Content-Disposition": f"attachment; filename=presentation_{file_id}.srt"
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
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )
