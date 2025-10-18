"""
Podcast routes for serving generated podcast files and scripts.

This module provides API endpoints for downloading and streaming generated
podcast files as well as fetching the dialogue used for audio generation.
"""

import json
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from loguru import logger

from slidespeaker.auth import extract_user_id, require_authenticated_user
from slidespeaker.configs.config import config, get_storage_provider
from slidespeaker.core.state_manager import state_manager
from slidespeaker.pipeline.podcast.coordinator import (
    extract_podcast_dialogue_from_state,
)
from slidespeaker.storage import StorageProvider
from slidespeaker.storage.paths import output_object_key

from .download_helpers import (
    build_cors_headers,
    build_headers,
    check_file_exists,
    file_id_from_task,
    proxy_cloud_media_with_range,
)

router = APIRouter(
    prefix="/api",
    tags=["podcast"],
    dependencies=[Depends(require_authenticated_user)],
)


# ---------------------------------------------------------------------------
# Podcast Download Endpoints
# ---------------------------------------------------------------------------


@router.get("/tasks/{task_id}/podcast")
async def get_podcast_by_task(task_id: str, request: Request) -> Any:
    """Serve podcast file for a task."""
    sp: StorageProvider = get_storage_provider()
    file_id: str | None = None

    try:
        file_id = await file_id_from_task(task_id)
    except HTTPException as exc:
        # Gracefully handle missing metadata; fall back to task-scoped checks
        if exc.status_code not in (400, 403, 404):
            raise
    if not file_id:
        try:
            mapped = await state_manager.get_file_id_by_task(task_id)
            if mapped:
                file_id = mapped
        except Exception:
            pass

    # Prefer the path recorded in state (compose step) when available.
    try:
        state = await state_manager.get_state(file_id) if file_id else None
        if not state:
            state = await state_manager.get_state_by_task(task_id)
        step_data = (
            (state or {}).get("steps", {}).get("compose_podcast", {}).get("data", {})
        )
        candidate_path = step_data.get("podcast_file")
        if isinstance(candidate_path, str):
            candidate = Path(candidate_path)
            if candidate.exists():
                logger.info(
                    "Serving podcast from state path {} for task {}",
                    candidate,
                    task_id,
                )
                return FileResponse(
                    str(candidate),
                    media_type="audio/mpeg",
                    filename=f"podcast_{task_id}.mp3",
                    headers=build_headers(
                        request,
                        content_type="audio/mpeg",
                        disposition=f"inline; filename=podcast_{task_id}.mp3",
                        cache_control="public, max-age=3600",
                    ),
                )
    except Exception as state_exc:
        logger.debug(
            "Unable to serve podcast via state path for task %s: %s",
            task_id,
            state_exc,
        )

    # Prefer task-id-first naming and only fall back to file-id when available
    candidate_keys: list[str] = [
        output_object_key(task_id, "podcast", "final.mp3"),
        f"{task_id}.mp3",
        f"{task_id}_podcast.mp3",
    ]
    if file_id:
        candidate_keys.insert(1, output_object_key(file_id, "podcast", "final.mp3"))
        candidate_keys.extend([f"{file_id}.mp3", f"{file_id}_podcast.mp3"])

    logger.info(
        "Podcast lookup for task {} (file_id={}): {}",
        task_id,
        file_id,
        candidate_keys,
    )

    # Try candidates without relying on provider-specific exists checks
    for object_key in candidate_keys:
        try:
            # Serve directly from local filesystem when artifact exists,
            # regardless of the configured storage provider. This protects
            # against cases where cloud uploads lag behind local writes.
            actual = config.output_dir / object_key
            if actual.exists():
                logger.info(
                    "Serving local podcast file {} (storage_provider={})",
                    actual,
                    config.storage_provider,
                )
                return FileResponse(
                    str(actual),
                    media_type="audio/mpeg",
                    filename=f"podcast_{task_id}.mp3",
                    headers=build_headers(
                        request,
                        content_type="audio/mpeg",
                        disposition=f"inline; filename=podcast_{task_id}.mp3",
                        cache_control="public, max-age=3600",
                    ),
                )

            if config.storage_provider == "local":
                # Already checked local path above; nothing else to do.
                continue

            # Cloud
            if config.proxy_cloud_media:
                range_header = request.headers.get("Range")
                return await proxy_cloud_media_with_range(
                    object_key, "audio/mpeg", range_header
                )

            # For OSS storage, avoid setting content_type to prevent header override errors
            get_file_url_kwargs = {
                "object_key": object_key,
                "expires_in": 300,
                "content_disposition": f"inline; filename=podcast_{task_id}.mp3",
            }

            # Only set content_type for non-OSS providers
            if config.storage_provider != "oss":
                get_file_url_kwargs["content_type"] = "audio/mpeg"

            url = sp.get_file_url(**get_file_url_kwargs)
            headers = build_cors_headers()
            headers["Location"] = url
            return Response(
                status_code=307,
                headers=headers,
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
async def download_podcast_by_task(task_id: str, request: Request) -> Any:
    """Download podcast file for a task."""
    sp: StorageProvider = get_storage_provider()

    file_id: str | None = None
    try:
        file_id = await file_id_from_task(task_id)
    except HTTPException as exc:
        if exc.status_code not in (400, 403, 404):
            raise
    if not file_id:
        try:
            mapped = await state_manager.get_file_id_by_task(task_id)
            if mapped:
                file_id = mapped
        except Exception:
            pass

    # Prefer state-recorded artifact when available.
    try:
        state = await state_manager.get_state(file_id) if file_id else None
        if not state:
            state = await state_manager.get_state_by_task(task_id)
        step_data = (
            (state or {}).get("steps", {}).get("compose_podcast", {}).get("data", {})
        )
        candidate_path = step_data.get("podcast_file")
        if isinstance(candidate_path, str):
            candidate = Path(candidate_path)
            if candidate.exists():
                logger.info(
                    "Serving podcast download from state path {} for task {}",
                    candidate,
                    task_id,
                )
                return FileResponse(
                    str(candidate),
                    media_type="audio/mpeg",
                    filename=f"podcast_{task_id}.mp3",
                    headers=build_headers(
                        request,
                        content_type="audio/mpeg",
                        disposition=f"attachment; filename=podcast_{task_id}.mp3",
                        cache_control="public, max-age=3600, must-revalidate",
                    ),
                )
    except Exception as state_exc:
        logger.debug(
            "Unable to serve podcast download via state path for task %s: %s",
            task_id,
            state_exc,
        )

    # Prefer task-id.mp3, then file-id.mp3, then legacy *_podcast.mp3 variants
    candidate_keys: list[str] = [
        output_object_key(task_id, "podcast", "final.mp3"),
        f"{task_id}.mp3",
        f"{task_id}_podcast.mp3",
    ]
    if file_id:
        candidate_keys.insert(1, output_object_key(file_id, "podcast", "final.mp3"))
        candidate_keys.extend([f"{file_id}.mp3", f"{file_id}_podcast.mp3"])

    logger.info(
        "Podcast download lookup for task {} (file_id={}): {}",
        task_id,
        file_id,
        candidate_keys,
    )

    object_key = next((k for k in candidate_keys if check_file_exists(k)), None)
    if object_key is None:
        logger.warning("Podcast file not found for task {}", task_id)
        raise HTTPException(status_code=404, detail="Podcast not found")

    actual = config.output_dir / object_key
    if actual.exists():
        return FileResponse(
            str(actual),
            media_type="audio/mpeg",
            filename=f"podcast_{task_id}.mp3",
            headers=build_headers(
                request,
                content_type="audio/mpeg",
                disposition=f"attachment; filename=podcast_{task_id}.mp3",
                cache_control="public, max-age=3600, must-revalidate",
            ),
        )
    else:
        logger.debug(
            "Podcast download local fallback missing: {} (storage_provider={})",
            actual,
            config.storage_provider,
        )
        # No local artifact, fall through to cloud handling
    if config.storage_provider == "local":
        # No artifact found locally; already exhausted candidates
        raise HTTPException(status_code=404, detail="Podcast not found")

    # For OSS storage, avoid setting content_type to prevent header override errors
    get_file_url_kwargs = {
        "object_key": object_key,
        "expires_in": 600,
        "content_disposition": f"attachment; filename=podcast_{task_id}.mp3",
    }

    # Only set content_type for non-OSS providers
    if config.storage_provider != "oss":
        get_file_url_kwargs["content_type"] = "audio/mpeg"

    url = sp.get_file_url(**get_file_url_kwargs)
    headers = build_cors_headers()
    headers["Location"] = url
    return Response(status_code=307, headers=headers)


# ---------------------------------------------------------------------------
# Podcast Script Endpoints
# ---------------------------------------------------------------------------


def _normalize_dialogue(items: list[Any]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        speaker = str(item.get("speaker", "")).strip()
        text = str(item.get("text", "")).strip()
        if speaker and text:
            normalized.append({"speaker": speaker, "text": text})
    return normalized


@router.get("/tasks/{task_id}/podcast/script")
async def get_podcast_script(
    task_id: str,
    current_user: Annotated[dict[str, Any], Depends(require_authenticated_user)],
) -> dict[str, Any]:
    """Return the structured podcast dialogue used for audio generation."""
    from slidespeaker.core.task_queue import task_queue
    from slidespeaker.repository.task import get_task as db_get_task

    user_id = extract_user_id(current_user)
    if not user_id:
        raise HTTPException(status_code=403, detail="user session missing id")

    db_row = await db_get_task(task_id)
    if not db_row or db_row.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Task not found")

    file_id = None
    if db_row.get("file_id"):
        file_id = str(db_row["file_id"])

    state = await state_manager.get_state_by_task(task_id)
    if not state and file_id:
        state = await state_manager.get_state(file_id)

    if not state:
        task = await task_queue.get_task(task_id)
        if task:
            file_id = (task.get("kwargs") or {}).get("file_id") or task.get("file_id")
            if isinstance(file_id, str):
                state = await state_manager.get_state(file_id)
    else:
        if not file_id and isinstance(state, dict):
            file_id = state.get("file_id")

    if state and isinstance(state, dict):
        st_owner = state.get("user_id")
        if isinstance(st_owner, str) and st_owner and st_owner != user_id:
            raise HTTPException(status_code=404, detail="Task not found")

    storage_provider = get_storage_provider()
    candidate_keys: list[str] = []
    candidate_keys.append(f"{task_id}_podcast_script.json")
    if isinstance(file_id, str) and file_id:
        candidate_keys.append(f"{file_id}_podcast_script.json")

    for key in dict.fromkeys(candidate_keys):
        try:
            if not storage_provider.file_exists(key):
                continue
            data = storage_provider.download_bytes(key)
            payload = json.loads(data.decode("utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        dialogue = payload.get("dialogue")
        if not isinstance(dialogue, list):
            continue
        normalized = _normalize_dialogue(dialogue)
        if not normalized:
            continue
        payload["dialogue"] = normalized
        if not payload.get("language"):
            payload["language"] = (
                (
                    state.get("podcast_transcript_language")
                    if isinstance(state, dict)
                    else db_row.get("subtitle_language")
                )
                or db_row.get("subtitle_language")
                or db_row.get("voice_language")
            )
        return payload

    # Legacy fallback: derive from state if storage artifact is unavailable
    legacy_payload = extract_podcast_dialogue_from_state(
        state if isinstance(state, dict) else None
    )
    if not legacy_payload:
        raise HTTPException(status_code=404, detail="Podcast script not found")

    normalized_dialogue = _normalize_dialogue(legacy_payload.get("dialogue") or [])
    if not normalized_dialogue:
        raise HTTPException(status_code=404, detail="Podcast script not found")

    legacy_payload["dialogue"] = normalized_dialogue
    return legacy_payload
