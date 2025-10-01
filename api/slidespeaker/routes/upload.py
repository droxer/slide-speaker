"""
Upload routes for handling file uploads.

This module provides API endpoints for uploading presentation files and initiating
the processing pipeline. It handles file validation, state initialization, and
task queue submission.
"""

import base64
import binascii
import hashlib
import json
from pathlib import Path
from typing import Any

import aiofiles
from fastapi import APIRouter, HTTPException, Request, UploadFile
from loguru import logger

from slidespeaker.configs.config import config
from slidespeaker.configs.locales import locale_utils
from slidespeaker.core.task_queue import task_queue

router = APIRouter(prefix="/api", tags=["upload"])

UPLOAD_DIR = config.uploads_dir


def _coerce_bool(value: Any, default: bool) -> bool:
    """Best-effort conversion of form/query values into booleans."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return bool(value)
    value_str = str(value).strip().lower()
    if value_str in {"true", "1", "yes", "on"}:
        return True
    if value_str in {"false", "0", "no", "off"}:
        return False
    return default


def _coerce_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    value_str = str(value).strip()
    return value_str or None


async def _parse_upload_payload(request: Request) -> dict[str, Any]:
    content_type = (request.headers.get("content-type") or "").lower()

    if "multipart/form-data" in content_type:
        form = await request.form()
        upload = form.get("file")

        file_bytes: bytes | None = None
        filename: str | None = None

        if isinstance(upload, UploadFile):
            file_bytes = await upload.read()
            filename = upload.filename or None
            await upload.close()
        else:
            # Support older clients that still send base64 strings ("file" or "file_data")
            raw_file = form.get("file_data") or form.get("file")
            if raw_file is None:
                raise HTTPException(
                    status_code=400, detail="File field 'file' is required"
                )

            logger.debug(
                "Legacy upload payload detected - type=%s preview=%s",
                type(raw_file).__name__,
                str(raw_file)[:128],
            )

            if isinstance(raw_file, bytes | bytearray):
                file_bytes = bytes(raw_file)
            else:
                raw_str = str(raw_file).strip()
                comma_idx = raw_str.find(",")
                candidate = raw_str[comma_idx + 1 :] if comma_idx != -1 else raw_str
                candidate = candidate.strip().replace("%2B", "+").replace(" ", "+")

                decoded_bytes: bytes | None = None
                if candidate:
                    try:
                        decoded_bytes = base64.b64decode(candidate, validate=True)
                    except (ValueError, binascii.Error):
                        try:
                            decoded_bytes = base64.b64decode(candidate)
                        except Exception:
                            decoded_bytes = None

                if decoded_bytes is None:
                    try:
                        parsed = json.loads(candidate)
                    except Exception:
                        parsed = None

                    if (
                        isinstance(parsed, dict)
                        and parsed.get("type") == "Buffer"
                        and isinstance(parsed.get("data"), list)
                    ):
                        try:
                            decoded_bytes = bytes(int(v) & 0xFF for v in parsed["data"])
                        except Exception:
                            decoded_bytes = None
                    elif isinstance(parsed, list):
                        try:
                            decoded_bytes = bytes(int(v) & 0xFF for v in parsed)
                        except Exception:
                            decoded_bytes = None

                if decoded_bytes is None:
                    # Handle simple comma/space separated integer payloads
                    parts = [p.strip() for p in candidate.split(",") if p.strip()]
                    if parts:
                        try:
                            decoded_bytes = bytes(int(p) & 0xFF for p in parts)
                        except Exception:
                            decoded_bytes = None

                if decoded_bytes is None:
                    raise HTTPException(status_code=400, detail="Invalid file payload")

                file_bytes = decoded_bytes

            filename = (
                _coerce_optional_str(form.get("filename"))
                or _coerce_optional_str(form.get("original_filename"))
                or _coerce_optional_str(form.get("name"))
            )

        if not filename:
            raise HTTPException(
                status_code=400, detail="Uploaded file is missing a filename"
            )
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        payload = {
            "filename": filename,
            "file_bytes": file_bytes,
            "voice_language": _coerce_optional_str(form.get("voice_language"))
            or "english",
            "subtitle_language": _coerce_optional_str(form.get("subtitle_language")),
            "transcript_language": _coerce_optional_str(
                form.get("transcript_language")
            ),
            "video_resolution": _coerce_optional_str(form.get("video_resolution"))
            or "hd",
            "generate_avatar": _coerce_bool(form.get("generate_avatar"), True),
            "generate_subtitles": _coerce_bool(form.get("generate_subtitles"), True),
            "generate_podcast": _coerce_bool(form.get("generate_podcast"), False),
            "generate_video": _coerce_bool(form.get("generate_video"), True),
            "task_type": _coerce_optional_str(form.get("task_type")),
            "source_type": _coerce_optional_str(form.get("source_type")),
        }
        return payload

    try:
        body = await request.json()
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    filename = _coerce_optional_str(body.get("filename"))
    file_data = body.get("file_data")

    if not filename or not file_data:
        raise HTTPException(
            status_code=400, detail="Filename and file data are required"
        )

    try:
        data_str = str(file_data).strip()
        comma_idx = data_str.find(",")
        candidate = data_str[comma_idx + 1 :] if comma_idx != -1 else data_str
        candidate = candidate.strip().replace("%2B", "+").replace(" ", "+")
        try:
            file_bytes = base64.b64decode(candidate, validate=True)
        except (ValueError, binascii.Error):
            file_bytes = base64.b64decode(candidate)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 file data") from exc

    return {
        "filename": filename,
        "file_bytes": file_bytes,
        "voice_language": _coerce_optional_str(body.get("voice_language")) or "english",
        "subtitle_language": _coerce_optional_str(body.get("subtitle_language")),
        "transcript_language": _coerce_optional_str(body.get("transcript_language")),
        "video_resolution": _coerce_optional_str(body.get("video_resolution")) or "hd",
        "generate_avatar": _coerce_bool(body.get("generate_avatar"), True),
        "generate_subtitles": _coerce_bool(body.get("generate_subtitles"), True),
        "generate_podcast": _coerce_bool(body.get("generate_podcast"), False),
        "generate_video": _coerce_bool(body.get("generate_video"), True),
        "task_type": _coerce_optional_str(body.get("task_type")),
        "source_type": _coerce_optional_str(body.get("source_type")),
    }


@router.post("/upload")
async def upload_file(request: Request) -> dict[str, str | None]:
    """Upload a presentation file and start processing."""
    try:
        payload = await _parse_upload_payload(request)
        filename = payload["filename"]
        file_bytes = payload["file_bytes"]

        # Normalize incoming languages to internal keys
        raw_voice_language = payload.get("voice_language", "english")
        raw_subtitle_language = payload.get("subtitle_language")
        raw_transcript_language = payload.get("transcript_language")
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
        video_resolution = payload.get("video_resolution", "hd")  # Default to HD
        generate_avatar = payload.get("generate_avatar", True)  # Default to True
        generate_subtitles = payload.get("generate_subtitles", True)
        generate_podcast = payload.get("generate_podcast", False)
        generate_video = payload.get("generate_video", True)

        file_ext = Path(filename).suffix.lower()
        # Determine source_type from request or by extension and validate
        source_type = payload.get("source_type")
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
        if (
            file_ext == ".pdf"
            and generate_podcast
            and payload.get("generate_video") is not True
        ):
            # If generate_video is not explicitly set to True, disable video generation
            # This covers cases where generate_video is False, None, or not present
            generate_video = False
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

        # Persist original to storage for future reruns
        try:
            sp = config.get_storage_provider()
            object_key = f"uploads/{file_id}{file_ext}"
            # Infer a reasonable content-type
            content_type = (
                "application/pdf"
                if file_ext == ".pdf"
                else (
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    if file_ext == ".pptx"
                    else (
                        "application/vnd.ms-powerpoint" if file_ext == ".ppt" else None
                    )
                )
            )
            sp.upload_file(str(file_path), object_key, content_type=content_type)
        except Exception as e:
            # Non-fatal: log and continue
            logger.warning(f"Failed to upload original to storage: {e}")

        # Normalize task_type and flags consistently
        # Prefer explicit task_type from request body when present; otherwise derive from flags
        req_task_type = (payload.get("task_type") or "").lower() or None
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
        logger.exception("Upload error")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}") from e
