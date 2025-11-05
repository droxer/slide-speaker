"""
File-based routes: rerun processing for an existing uploaded file.

This endpoint allows creating new tasks for a previously uploaded file_id using
the stored original in uploads/ or cloud storage.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from slidespeaker.auth import extract_user_id, require_authenticated_user
from slidespeaker.configs.config import config
from slidespeaker.configs.db import db_enabled
from slidespeaker.configs.locales import locale_utils
from slidespeaker.core.task_queue import task_queue
from slidespeaker.repository.upload import get_upload
from slidespeaker.storage.paths import (
    build_storage_uri,
    object_key_from_uri,
    upload_object_key,
)

router = APIRouter(
    prefix="/api",
    tags=["files"],
    dependencies=[Depends(require_authenticated_user)],
)


@router.post("/files/{file_id}/run")
async def run_file(
    file_id: str,
    payload: dict[str, Any],
    current_user: Annotated[dict[str, Any], Depends(require_authenticated_user)],
) -> dict[str, Any]:
    """Create a new task for an existing file_id.

    Body: {
      task_type: 'video'|'podcast'|'both',
      voice_language: str,
      subtitle_language?: str|null,
      transcript_language?: str|null,
      video_resolution?: 'sd'|'hd'|'fullhd'
    }
    """
    # Lookup filename/ext from state if available
    from slidespeaker.core.state_manager import state_manager

    st = await state_manager.get_state(file_id)
    filename = (st or {}).get("filename") or f"{file_id}"
    file_ext = (st or {}).get("file_ext") or ""
    upload_record: dict[str, Any] | None = None
    if db_enabled:
        try:
            upload_record = await get_upload(file_id)
        except Exception as exc:
            logger.warning(f"Failed to load upload metadata for {file_id}: {exc}")
    if upload_record:
        if (not isinstance(file_ext, str) or not file_ext) and upload_record.get(
            "file_ext"
        ):
            file_ext = upload_record["file_ext"] or ""
        upload_filename = upload_record.get("filename")
        if upload_filename:
            filename = upload_filename
    if not isinstance(file_ext, str) or not file_ext:
        # Try to infer by scanning uploads dir
        up = config.uploads_dir
        for ext in (".pdf", ".pptx", ".ppt"):
            if (up / f"{file_id}{ext}").exists():
                file_ext = ext
                break
    if not file_ext:
        raise HTTPException(
            status_code=404, detail="Original file not found (unknown extension)"
        )

    user_id = extract_user_id(current_user)
    if not user_id:
        raise HTTPException(status_code=403, detail="user session missing id")

    if st and isinstance(st, dict):
        existing_owner = st.get("user_id")
        if (
            isinstance(existing_owner, str)
            and existing_owner
            and existing_owner != user_id
        ):
            raise HTTPException(status_code=403, detail="forbidden")
    if upload_record:
        upload_owner = upload_record.get("user_id")
        if isinstance(upload_owner, str) and upload_owner and upload_owner != user_id:
            raise HTTPException(status_code=403, detail="forbidden")

    # Ensure local copy exists in uploads dir
    uploads_path = config.uploads_dir
    uploads_path.mkdir(parents=True, exist_ok=True)
    file_path = uploads_path / f"{file_id}{file_ext}"
    upload_storage_entry = (upload_record or {}).get("storage_path")
    storage_object_key = object_key_from_uri(upload_storage_entry)
    if not storage_object_key:
        storage_object_key = upload_object_key(file_id, file_ext)
    storage_uri = build_storage_uri(storage_object_key)
    if not file_path.exists():
        # Attempt to fetch from configured storage
        try:
            sp = config.get_storage_provider()
            sp.download_file(storage_object_key, file_path)
        except Exception as e:
            logger.error(f"Failed to download original from storage: {e}")
            raise HTTPException(
                status_code=500, detail="Original file not available"
            ) from e

    # Resolve options
    task_type = str(payload.get("task_type") or "video").lower()
    voice_language = locale_utils.normalize_language(
        payload.get("voice_language") or "english"
    )
    raw_voice_id = payload.get("voice_id")
    voice_id = (
        raw_voice_id.strip()
        if isinstance(raw_voice_id, str) and raw_voice_id.strip()
        else None
    )
    subtitle_language = payload.get("subtitle_language")
    transcript_language = payload.get("transcript_language")
    if subtitle_language is not None:
        subtitle_language = locale_utils.normalize_language(subtitle_language)
    if transcript_language is not None:
        transcript_language = locale_utils.normalize_language(transcript_language)
    video_resolution = str(payload.get("video_resolution") or "hd")
    raw_host_voice = payload.get("podcast_host_voice")
    podcast_host_voice = (
        raw_host_voice.strip()
        if isinstance(raw_host_voice, str) and raw_host_voice.strip()
        else None
    )
    raw_guest_voice = payload.get("podcast_guest_voice")
    podcast_guest_voice = (
        raw_guest_voice.strip()
        if isinstance(raw_guest_voice, str) and raw_guest_voice.strip()
        else None
    )

    # Fallback to previous selections when not provided
    if st and isinstance(st, dict):
        if voice_id is None:
            stored_voice = st.get("voice_id") or (
                (st.get("task_config") or {}).get("voice_id")
                if isinstance(st.get("task_config"), dict)
                else None
            )
            if isinstance(stored_voice, str) and stored_voice.strip():
                voice_id = stored_voice.strip()
        if podcast_host_voice is None:
            stored_host = st.get("podcast_host_voice") or (
                (st.get("task_config") or {}).get("podcast_host_voice")
                if isinstance(st.get("task_config"), dict)
                else None
            )
            if isinstance(stored_host, str) and stored_host.strip():
                podcast_host_voice = stored_host.strip()
        if podcast_guest_voice is None:
            stored_guest = st.get("podcast_guest_voice") or (
                (st.get("task_config") or {}).get("podcast_guest_voice")
                if isinstance(st.get("task_config"), dict)
                else None
            )
            if isinstance(stored_guest, str) and stored_guest.strip():
                podcast_guest_voice = stored_guest.strip()

    # Enforce permissible combinations
    if file_ext.lower() != ".pdf" and task_type == "podcast":
        raise HTTPException(
            status_code=400, detail="Podcast reruns are only supported for PDF files"
        )

    # Flags
    generate_video = task_type in ("video", "both")
    generate_podcast = task_type in ("podcast", "both")

    if not generate_video:
        voice_id = None
    if not generate_podcast:
        podcast_host_voice = None
        podcast_guest_voice = None

    upload_source_type = upload_record.get("source_type") if upload_record else None
    source_type = (
        upload_source_type
        if upload_source_type
        else ("pdf" if file_ext.lower() == ".pdf" else "slides")
    )
    if source_type == "audio":
        if not generate_podcast:
            raise HTTPException(
                status_code=400,
                detail="Audio uploads require podcast generation",
            )
        generate_video = bool(payload.get("generate_video", False))
        voice_id = None
    checksum = upload_record.get("checksum") if upload_record else None
    size_bytes = upload_record.get("size_bytes") if upload_record else None
    if size_bytes is None:
        try:
            size_bytes = file_path.stat().st_size
        except OSError:
            size_bytes = None
    content_type = upload_record.get("content_type") if upload_record else None

    # Submit new task
    try:
        voice_for_task = voice_id if generate_video else None
        host_voice_for_task = podcast_host_voice if generate_podcast else None
        guest_voice_for_task = podcast_guest_voice if generate_podcast else None
        new_task_id = await task_queue.submit_task(
            task_type,
            user_id=user_id,
            file_id=file_id,
            file_path=str(file_path),
            file_ext=file_ext,
            filename=filename,
            source_type=source_type,
            checksum=checksum,
            file_size=size_bytes,
            content_type=content_type,
            storage_object_key=storage_object_key,
            storage_uri=storage_uri,
            voice_language=voice_language,
            subtitle_language=subtitle_language,
            transcript_language=transcript_language,
            video_resolution=video_resolution,
            generate_avatar=False,
            generate_subtitles=True,
            generate_podcast=generate_podcast,
            generate_video=generate_video,
            voice_id=voice_for_task,
            podcast_host_voice=host_voice_for_task,
            podcast_guest_voice=guest_voice_for_task,
        )
        return {"task_id": new_task_id, "file_id": file_id}
    except Exception as e:
        logger.error(f"Failed to submit rerun task: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit task") from e
