"""
Upload routes for handling file uploads.

This module provides API endpoints for uploading presentation files and initiating
the processing pipeline. It handles file validation, state initialization, and
task queue submission.
"""

import base64
import hashlib
from pathlib import Path

import aiofiles
from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from slidespeaker.configs.config import config
from slidespeaker.configs.locales import locale_utils
from slidespeaker.core.task_queue import task_queue

router = APIRouter(prefix="/api", tags=["upload"])

UPLOAD_DIR = config.uploads_dir


@router.post("/upload")
async def upload_file(request: Request) -> dict[str, str | None]:
    """Upload a presentation file and start processing."""
    try:
        # Parse JSON data from request body
        body = await request.json()
        filename = body.get("filename")
        file_data = body.get("file_data")
        # Normalize incoming languages to internal keys
        raw_voice_language = body.get("voice_language", "english")
        raw_subtitle_language = body.get("subtitle_language")
        raw_transcript_language = body.get("transcript_language")
        voice_language = locale_utils.normalize_language(raw_voice_language)
        subtitle_language = (
            locale_utils.normalize_language(raw_subtitle_language)
            if raw_subtitle_language is not None
            else None
        )  # Don't default to audio language
        transcript_language = (
            locale_utils.normalize_language(raw_transcript_language)
            if raw_transcript_language is not None
            else None
        )
        video_resolution = body.get("video_resolution", "hd")  # Default to HD
        generate_avatar = body.get("generate_avatar", True)  # Default to True
        generate_subtitles = True  # Always generate subtitles by default
        generate_podcast = body.get("generate_podcast", False)
        generate_video = body.get("generate_video", True)

        if not filename or not file_data:
            raise HTTPException(
                status_code=400, detail="Filename and file data are required"
            )

        # Decode base64 file data
        file_bytes = base64.b64decode(file_data)

        file_ext = Path(filename).suffix.lower()
        # Determine source_type from request or by extension and validate
        source_type = body.get("source_type")
        if not source_type:
            source_type = (
                "pdf"
                if file_ext == ".pdf"
                else ("slides" if file_ext in [".pptx", ".ppt"] else None)
            )
        # Validate provided/derived source_type strictly
        if source_type not in ("pdf", "slides"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source_type: {source_type}. Must be 'pdf' or 'slides'.",
            )
        # For PDF files, if user selects podcast generation, default to podcast-only unless
        # they explicitly request video as well. This prevents accidental video generation
        # when user only wants podcast.
        if file_ext == ".pdf" and generate_podcast:
            logger.info(
                f"PDF podcast request: generate_video={body.get('generate_video')}, "
                f"will generate video: {generate_video}"
            )
            # If generate_video is not explicitly set to True, disable video generation
            # This covers cases where generate_video is False, None, or not present
            if body.get("generate_video") is not True:
                generate_video = False
                logger.info("Disabled video generation for podcast-only request")
        if file_ext not in [".pdf", ".pptx", ".ppt"]:
            raise HTTPException(
                status_code=400, detail="Only PDF and PowerPoint files are supported"
            )

        # Validate languages
        if not locale_utils.validate_language(voice_language):
            raise HTTPException(
                status_code=400, detail=f"Unsupported voice language: {voice_language}"
            )

        if subtitle_language and not locale_utils.validate_language(subtitle_language):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported subtitle language: {subtitle_language}",
            )

        # Validate video resolution
        valid_resolutions = ["sd", "hd", "fullhd"]
        if video_resolution not in valid_resolutions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported video resolution: {video_resolution}. "
                f"Valid options: {', '.join(valid_resolutions)}",
            )

        # Generate hash-based ID
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        file_id = file_hash[:16]  # Use first 16 chars of hash
        file_path = UPLOAD_DIR / f"{file_id}{file_ext}"

        # Write file to disk
        async with aiofiles.open(file_path, "wb") as out_file:
            await out_file.write(file_bytes)

        # Normalize task_type and flags consistently
        # Prefer explicit task_type from request body when present; otherwise derive from flags
        req_task_type = (body.get("task_type") or "").lower() or None
        if req_task_type in ("video", "podcast", "both"):
            task_type = req_task_type
        else:
            task_type = (
                "both"
                if (generate_video and generate_podcast)
                else (
                    "podcast" if (generate_podcast and not generate_video) else "video"
                )
            )

        # Enforce flags based on task_type, especially for PDFs
        if task_type == "podcast":
            generate_podcast = True
            generate_video = False
        elif task_type == "both":
            generate_podcast = True
            generate_video = True
        else:  # video
            generate_podcast = False
            generate_video = True

        logger.info(
            f"Upload normalization - source_type: {source_type}, task_type: {task_type}, "
            f"generate_video: {generate_video}, generate_podcast: {generate_podcast}"
        )

        # Submit task to Redis task queue (state management is handled internally)
        task_id = await task_queue.submit_task(
            task_type,
            file_id=file_id,
            file_path=str(file_path),
            file_ext=file_ext,
            filename=filename,
            source_type=source_type,
            voice_language=voice_language,
            subtitle_language=subtitle_language,
            transcript_language=transcript_language,
            video_resolution=video_resolution,
            generate_avatar=generate_avatar,
            generate_subtitles=generate_subtitles,
            generate_podcast=generate_podcast,
            generate_video=generate_video,
        )

        logger.info(
            f"File uploaded: {file_id}, type: {file_ext}, task submitted: {task_id}"
        )

        return {
            "file_id": file_id,
            "task_id": task_id,
            "message": "File uploaded successfully, processing started in background",
        }

    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}") from e
