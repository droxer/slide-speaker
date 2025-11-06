"""
Podcast routes for serving generated podcast files and scripts.

This module provides API endpoints for downloading and streaming generated
podcast files as well as fetching the dialogue used for audio generation.
"""

import json
import re
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


def _normalize_dialogue(items: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        speaker = str(item.get("speaker", "")).strip()
        text = str(item.get("text", "")).strip()
        if speaker and text:
            entry: dict[str, Any] = {"speaker": speaker, "text": text}
            voice = item.get("voice")
            if isinstance(voice, str) and voice.strip():
                entry["voice"] = voice.strip()
            segment_file = item.get("segment_file")
            if isinstance(segment_file, str) and segment_file.strip():
                entry["segment_file"] = segment_file.strip()
            for key in ("start", "end", "duration"):
                value = item.get(key)
                if isinstance(value, int | float):
                    entry[key] = float(value)
            normalized.append(entry)
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


def _normalize_cues(items: list[Any]) -> list[dict[str, float | str]]:
    normalized: list[dict[str, float | str]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        start = item.get("start")
        end = item.get("end")
        start_val = float(start) if isinstance(start, int | float) else None
        end_val = float(end) if isinstance(end, int | float) else None
        if start_val is None or end_val is None:
            continue
        normalized.append(
            {
                "start": start_val,
                "end": end_val,
                "text": text,
            }
        )
    return normalized


def _resolve_subtitle_url(
    storage_provider: StorageProvider,
    storage_keys: list[str],
    storage_urls: list[str],
    suffix: str,
) -> str | None:
    for key in storage_keys:
        if isinstance(key, str) and key.endswith(suffix):
            try:
                return storage_provider.get_file_url(
                    key,
                    expires_in=300,
                    content_disposition=f"inline; filename={Path(key).name}",
                )
            except Exception:
                continue
    for url in storage_urls:
        if isinstance(url, str) and url.endswith(suffix):
            return url
    return None


def _load_vtt_from_storage(
    *,
    storage_provider: StorageProvider,
    storage_keys: list[str],
    subtitle_files: list[str],
    artifacts: dict[str, Any] | None,
) -> str | None:
    candidates: list[tuple[str, str]] = []

    def append_candidate(kind: str, value: str) -> None:
        if isinstance(value, str) and value.strip():
            candidates.append((kind, value.strip()))

    for key in storage_keys:
        if isinstance(key, str) and key.endswith(".vtt"):
            append_candidate("storage_key", key)

    for path in subtitle_files:
        if isinstance(path, str) and path.endswith(".vtt"):
            append_candidate("local_path", path)

    if artifacts and isinstance(artifacts, dict):
        art_vtt = (
            artifacts.get("podcast", {})
            if isinstance(artifacts.get("podcast"), dict)
            else {}
        )
        vtt_entry = art_vtt.get("subtitles")
        if isinstance(vtt_entry, dict):
            vtt_info = vtt_entry.get("vtt")
            if isinstance(vtt_info, dict):
                append_candidate("local_path", str(vtt_info.get("local_path") or ""))
                append_candidate("storage_key", str(vtt_info.get("storage_key") or ""))

    for kind, value in candidates:
        try:
            if kind == "local_path":
                path = Path(value)
                if path.exists():
                    return path.read_text(encoding="utf-8")
            else:
                data = storage_provider.download_bytes(value)
                return data.decode("utf-8")
        except Exception:
            continue
    return None


def _parse_vtt_to_cues(text: str) -> list[dict[str, float | str]]:
    time_re = re.compile(
        r"(\d{2}):(\d{2}):(\d{2})[.,](\d{3})\s+-->\s+(\d{2}):(\d{2}):(\d{2})[.,](\d{3})"
    )

    def to_seconds(parts: tuple[str, ...]) -> float:
        h, m, s, ms = parts
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

    lines = text.splitlines()
    cues: list[dict[str, float | str]] = []
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        idx += 1
        if not line or line.upper() == "WEBVTT" or line.isdigit():
            continue
        match = time_re.match(line)
        if not match:
            continue
        start = to_seconds(match.groups()[0:4])
        end = to_seconds(match.groups()[4:8])
        payload: list[str] = []
        while idx < len(lines):
            text_line = lines[idx].strip()
            if not text_line:
                idx += 1
                break
            if time_re.match(text_line):
                break
            payload.append(text_line)
            idx += 1
        cue_text = "\n".join(payload).strip()
        if cue_text:
            cues.append({"start": start, "end": end, "text": cue_text})
    return cues


@router.get("/tasks/{task_id}/podcast/subtitles")
async def get_podcast_subtitles(
    task_id: str,
    current_user: Annotated[dict[str, Any], Depends(require_authenticated_user)],
) -> dict[str, Any]:
    """Return structured cues and download links for podcast subtitles."""
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

    if not state:
        raise HTTPException(status_code=404, detail="Task state not found")

    steps = state.get("steps") if isinstance(state.get("steps"), dict) else {}
    subtitle_step = (
        steps.get("generate_podcast_subtitles") if isinstance(steps, dict) else None
    )
    subtitle_data = (
        subtitle_step.get("data")
        if isinstance(subtitle_step, dict)
        and isinstance(subtitle_step.get("data"), dict)
        else {}
    )

    subtitle_files = (
        subtitle_data.get("subtitle_files")
        if isinstance(subtitle_data.get("subtitle_files"), list)
        else []
    )
    artifacts = (
        state.get("artifacts") if isinstance(state.get("artifacts"), dict) else {}
    )

    storage_provider = get_storage_provider()
    storage_keys = (
        subtitle_data.get("storage_keys")
        if isinstance(subtitle_data.get("storage_keys"), list)
        else []
    )
    storage_urls = (
        subtitle_data.get("storage_urls")
        if isinstance(subtitle_data.get("storage_urls"), list)
        else []
    )

    vtt_text = _load_vtt_from_storage(
        storage_provider=storage_provider,
        storage_keys=[str(k) for k in storage_keys if isinstance(k, str)],
        subtitle_files=[str(p) for p in subtitle_files if isinstance(p, str)],
        artifacts=artifacts if isinstance(artifacts, dict) else {},
    )

    cues = _parse_vtt_to_cues(vtt_text) if vtt_text else []
    if not cues:
        cues = _normalize_cues(subtitle_data.get("dialogue_entries") or [])
    if not cues:
        payload = extract_podcast_dialogue_from_state(state)
        cues = _normalize_cues((payload or {}).get("dialogue") or [])
    if not cues:
        raise HTTPException(status_code=404, detail="Podcast subtitles not found")

    vtt_url = _resolve_subtitle_url(
        storage_provider, storage_keys, storage_urls, ".vtt"
    )
    srt_url = _resolve_subtitle_url(
        storage_provider, storage_keys, storage_urls, ".srt"
    )

    return {
        "cues": cues,
        "vtt_url": vtt_url,
        "srt_url": srt_url,
    }
