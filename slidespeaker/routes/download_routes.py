"""
Download routes for serving generated files.

This module provides API endpoints for downloading generated presentation videos
and subtitle files. It handles file serving with appropriate content types and headers.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from slidespeaker.auth import require_authenticated_user
from slidespeaker.storage.paths import output_object_key

from .download_helpers import file_id_from_task, final_audio_object_keys

router = APIRouter(
    prefix="/api",
    tags=["downloads"],
    dependencies=[Depends(require_authenticated_user)],
)


@router.get("/tasks/{task_id}/downloads")
async def list_downloads(task_id: str) -> dict[str, Any]:
    """Provide a consolidated list of download links for a task.

    Includes video (inline and download), audio (inline and download),
    subtitles (available locales and formats), and transcript markdown.
    """
    from .download_helpers import check_file_exists

    file_id: str | None = None
    try:
        file_id = await file_id_from_task(task_id)
    except HTTPException as exc:
        if exc.status_code not in (400, 403, 404):
            raise
    if not file_id:
        try:
            from slidespeaker.core.state_manager import state_manager as sm

            mapped = await sm.get_file_id_by_task(task_id)
            if mapped:
                file_id = mapped
        except Exception:
            pass
    items: list[dict[str, Any]] = []

    # Get task information once to avoid duplicate queries
    task_type = None
    subtitle_language = None
    voice_language = None

    # Try to get task info from database first
    try:
        from slidespeaker.repository.task import get_task

        row = await get_task(task_id)
        if row is not None:
            task_type = (row.get("task_type") or "").lower()
            subtitle_language = row.get("subtitle_language")
            voice_language = row.get("voice_language")
    except Exception:
        # Fallback to state if DB unavailable
        try:
            from slidespeaker.core.state_manager import state_manager as sm

            st = await sm.get_state_by_task(task_id)
            if st is not None:
                task_type = (st.get("task_type") or "").lower()
                subtitle_language = st.get("subtitle_language")
                voice_language = st.get("voice_language")
        except Exception:
            pass

    # Video - only for non-podcast tasks
    if task_type != "podcast":
        video_candidates = [
            output_object_key(task_id, "video", "final.mp4"),
            f"{task_id}.mp4",
        ]
        if file_id:
            video_candidates.insert(1, output_object_key(file_id, "video", "final.mp4"))
            video_candidates.extend([f"{file_id}.mp4", f"{file_id}_final.mp4"])
        video_exists = any(check_file_exists(k) for k in video_candidates)
    else:
        video_exists = False

    if video_exists:
        items.append(
            {
                "type": "video",
                "url": f"/api/tasks/{task_id}/video",
                "download_url": f"/api/tasks/{task_id}/video/download",
            }
        )

    # Final audio - only for non-podcast tasks (podcast tasks use separate podcast endpoint)
    if task_type != "podcast":
        if file_id:
            audio_keys = final_audio_object_keys(file_id, task_id=task_id)
        else:
            audio_keys = [
                output_object_key(task_id, "audio", "final.mp3"),
                f"{task_id}.mp3",
                f"{task_id}_final_audio.mp3",
                f"{task_id}_final.mp3",
            ]
        audio_exists = any(check_file_exists(k) for k in audio_keys)
        if audio_exists:
            items.append(
                {
                    "type": "audio",
                    "url": f"/api/tasks/{task_id}/audio",
                    "download_url": f"/api/tasks/{task_id}/audio/download",
                }
            )

    # Podcast MP3 (for podcast-only tasks) - use different endpoint
    if task_type == "podcast":
        # Prefer structured outputs, fallback to legacy keys
        podcast_keys = [
            output_object_key(task_id, "podcast", "final.mp3"),
            f"{task_id}.mp3",
            f"{task_id}_podcast.mp3",
        ]
        if file_id:
            podcast_keys.insert(1, output_object_key(file_id, "podcast", "final.mp3"))
            podcast_keys.extend([f"{file_id}.mp3", f"{file_id}_podcast.mp3"])
        podcast_exists = any(check_file_exists(k) for k in podcast_keys)

        if podcast_exists:
            items.append(
                {
                    "type": "podcast",
                    "url": f"/api/tasks/{task_id}/podcast",
                    "download_url": f"/api/tasks/{task_id}/podcast/download",
                }
            )

    # Subtitles by locale — consolidated language resolution
    from slidespeaker.configs.locales import locale_utils

    preferred_locales: list[str] = []

    # Determine preferred locale from task info
    lang = subtitle_language or voice_language
    if isinstance(lang, str) and lang:
        preferred_locales.append(locale_utils.get_locale_code(lang))

    # Fallback to state if DB lacked languages
    if not preferred_locales and file_id:
        try:
            from slidespeaker.core.state_manager import state_manager as sm2

            st = await sm2.get_state(file_id)
            if st:
                lang = st.get("subtitle_language") or st.get("voice_language")
                if isinstance(lang, str) and lang:
                    preferred_locales.append(locale_utils.get_locale_code(lang))
                # Inspect subtitle_files if present to extract locale codes
                try:
                    step = (st.get("steps") or {}).get("generate_subtitles") or {}
                    data = step.get("data") or {}
                    files = data.get("subtitle_files") or []
                    import re as _re

                    for p in files:
                        if not isinstance(p, str):
                            continue
                        m = _re.search(r"_([A-Za-z-]+)\.(vtt|srt)$", p)
                        if m:
                            preferred_locales.append(m.group(1))
                except Exception:
                    pass
                # Include locales referenced in structured artifacts map
                try:
                    artifacts = st.get("artifacts") or {}
                    subtitle_artifacts = (
                        artifacts.get("subtitles")
                        if isinstance(artifacts, dict)
                        else {}
                    )
                    if isinstance(subtitle_artifacts, dict):
                        for loc_code in subtitle_artifacts:
                            if isinstance(loc_code, str) and loc_code:
                                preferred_locales.append(loc_code)
                except Exception:
                    pass
        except Exception:
            pass

    # Check for existing subtitle files
    seen_locales: set[str] = set()
    for loc in preferred_locales:
        subtitle_candidates = [
            output_object_key(task_id, "subtitles", f"{loc}.vtt"),
            output_object_key(task_id, "subtitles", f"{loc}.srt"),
            f"{task_id}_{loc}.vtt",
            f"{task_id}_{loc}.srt",
        ]
        if file_id:
            subtitle_candidates.insert(
                2, output_object_key(file_id, "subtitles", f"{loc}.vtt")
            )
            subtitle_candidates.insert(
                3, output_object_key(file_id, "subtitles", f"{loc}.srt")
            )
        if any(check_file_exists(k) for k in subtitle_candidates):
            seen_locales.add(loc)

    # Add subtitle items
    for loc in sorted(seen_locales):
        # VTT
        items.append(
            {
                "type": "vtt_subtitles",
                "language": loc,
                "url": f"/api/tasks/{task_id}/subtitles/vtt?language={loc}",
                "download_url": f"/api/tasks/{task_id}/subtitles/vtt/download?language={loc}",
            }
        )
        # SRT
        items.append(
            {
                "type": "srt_subtitles",
                "language": loc,
                "url": f"/api/tasks/{task_id}/subtitles/srt?language={loc}",
                "download_url": f"/api/tasks/{task_id}/subtitles/srt/download?language={loc}",
            }
        )

    # Transcript (Markdown) always linkable; handler decides availability
    items.append(
        {
            "type": "transcript",
            "url": f"/api/tasks/{task_id}/transcripts/markdown",
        }
    )

    return {"task_id": task_id, "file_id": file_id, "items": items}
