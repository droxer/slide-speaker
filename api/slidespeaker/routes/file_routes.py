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
from slidespeaker.configs.locales import locale_utils
from slidespeaker.core.task_queue import task_queue

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

    owner_id = extract_user_id(current_user)
    if not owner_id:
        raise HTTPException(status_code=403, detail="user session missing id")

    if st and isinstance(st, dict):
        existing_owner = st.get("owner_id")
        if (
            isinstance(existing_owner, str)
            and existing_owner
            and existing_owner != owner_id
        ):
            raise HTTPException(status_code=403, detail="forbidden")

    # Ensure local copy exists in uploads dir
    uploads_path = config.uploads_dir
    uploads_path.mkdir(parents=True, exist_ok=True)
    file_path = uploads_path / f"{file_id}{file_ext}"
    if not file_path.exists():
        # Attempt to fetch from configured storage
        try:
            sp = config.get_storage_provider()
            object_key = f"uploads/{file_id}{file_ext}"
            sp.download_file(object_key, file_path)
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
    subtitle_language = payload.get("subtitle_language")
    transcript_language = payload.get("transcript_language")
    if subtitle_language is not None:
        subtitle_language = locale_utils.normalize_language(subtitle_language)
    if transcript_language is not None:
        transcript_language = locale_utils.normalize_language(transcript_language)
    video_resolution = str(payload.get("video_resolution") or "hd")

    # Enforce permissible combinations
    if file_ext.lower() != ".pdf" and task_type == "podcast":
        raise HTTPException(
            status_code=400, detail="Podcast reruns are only supported for PDF files"
        )

    # Flags
    generate_video = task_type in ("video", "both")
    generate_podcast = task_type in ("podcast", "both")

    # Submit new task
    try:
        new_task_id = await task_queue.submit_task(
            task_type,
            owner_id=owner_id,
            file_id=file_id,
            file_path=str(file_path),
            file_ext=file_ext,
            filename=filename,
            source_type=("pdf" if file_ext.lower() == ".pdf" else "slides"),
            voice_language=voice_language,
            subtitle_language=subtitle_language,
            transcript_language=transcript_language,
            video_resolution=video_resolution,
            generate_avatar=False,
            generate_subtitles=True,
            generate_podcast=generate_podcast,
            generate_video=generate_video,
        )
        return {"task_id": new_task_id, "file_id": file_id}
    except Exception as e:
        logger.error(f"Failed to submit rerun task: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit task") from e
