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
from slidespeaker.core.state_manager import state_manager
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
        voice_language = locale_utils.normalize_language(raw_voice_language)
        subtitle_language = (
            locale_utils.normalize_language(raw_subtitle_language)
            if raw_subtitle_language is not None
            else None
        )  # Don't default to audio language
        video_resolution = body.get("video_resolution", "hd")  # Default to HD
        generate_avatar = body.get("generate_avatar", True)  # Default to True
        generate_subtitles = True  # Always generate subtitles by default

        if not filename or not file_data:
            raise HTTPException(
                status_code=400, detail="Filename and file data are required"
            )

        # Decode base64 file data
        file_bytes = base64.b64decode(file_data)

        file_ext = Path(filename).suffix.lower()
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

        # Submit task to Redis task queue first (so we can store state task-first)
        task_id = await task_queue.submit_task(
            "process_presentation",
            file_id=file_id,
            file_path=str(file_path),
            file_ext=file_ext,
            filename=filename,
            voice_language=voice_language,
            subtitle_language=subtitle_language,
            video_resolution=video_resolution,
            generate_avatar=generate_avatar,
            generate_subtitles=generate_subtitles,
        )

        # Create initial state (task-first; mirrors to task alias and mappings)
        await state_manager.create_state(
            file_id,
            file_path,
            file_ext,
            filename,
            voice_language,
            subtitle_language,
            video_resolution,
            generate_avatar,
            generate_subtitles,
            task_id=task_id,
        )

        logger.info(
            f"File uploaded: {file_id}, type: {file_ext}, task submitted: {task_id}"
        )

        # Bind task_id <-> file_id (redundant when create_state passed task_id; kept for safety)
        try:
            await state_manager.bind_task(file_id, task_id)
        except Exception as save_err:
            logger.warning(f"Failed to bind task_id in state manager: {save_err}")

        return {
            "file_id": file_id,
            "task_id": task_id,
            "message": "File uploaded successfully, processing started in background",
        }

    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}") from e
