"""
Transcript routes for serving final revised Markdown transcripts.

Exposes an endpoint to retrieve the final (revised) transcript in Markdown
for both PDF and slide pipelines. Falls back to generating Markdown from
the revised transcript list if the pre-rendered Markdown is not present.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response

from slidespeaker.auth import require_authenticated_user
from slidespeaker.core.state_manager import state_manager
from slidespeaker.transcript.markdown import transcripts_to_markdown

router = APIRouter(
    prefix="/api",
    tags=["transcripts"],
    dependencies=[Depends(require_authenticated_user)],
)


@router.get("/tasks/{task_id}/transcripts/markdown")
async def get_final_markdown_transcript_by_task(task_id: str) -> Response:
    """Task-based transcript endpoint.

    Prefers revised transcripts in state; falls back to building Markdown
    from available step data; finally falls back to uploaded transcript file.
    """
    from slidespeaker.configs.config import get_storage_provider
    from slidespeaker.core.task_queue import task_queue
    from slidespeaker.repository.task import get_task as db_get_task

    # Resolve file_id and load state (prefer task-based state)
    state = await state_manager.get_state_by_task(task_id)
    file_id: str | None = None
    if not state:
        # DB fallback: task_id -> file_id
        row = await db_get_task(task_id)
        file_id = str(row["file_id"]) if row and row.get("file_id") else None
        if file_id:
            state = await state_manager.get_state(file_id)
    # Queue fallback: task payload mapping
    if not state:
        task = await task_queue.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        file_id = (task.get("kwargs") or {}).get("file_id") or task.get("file_id")
        if not file_id or not isinstance(file_id, str):
            raise HTTPException(status_code=404, detail="File not found for task")
        state = await state_manager.get_state(file_id)
    if state and "steps" in state:
        steps = state["steps"]
        # Prefer translated podcast conversation when available; else original
        pod = None
        pod_translated = steps.get("translate_podcast_script")
        pod_original = steps.get("generate_podcast_script")
        if pod_translated and pod_translated.get("status") == "completed":
            pod = pod_translated
        elif pod_original and pod_original.get("status") == "completed":
            pod = pod_original

        if pod and pod.get("status") == "completed":
            data = pod.get("data") or []
            if isinstance(data, list) and data:
                # Try to fetch voices from podcast audio step
                host_voice = None
                guest_voice = None
                try:
                    ga = steps.get("generate_podcast_audio") or {}
                    if (ga.get("status") == "completed") and isinstance(
                        ga.get("data"), dict
                    ):
                        host_voice = (
                            (ga["data"].get("host_voice") or None)
                            if isinstance(ga["data"], dict)
                            else None
                        )
                        guest_voice = (
                            (ga["data"].get("guest_voice") or None)
                            if isinstance(ga["data"], dict)
                            else None
                        )
                except Exception:
                    pass
                # Build conversation-style Markdown
                lines: list[str] = ["# Podcast Conversation\n"]
                for item in data:
                    if isinstance(item, dict):
                        raw_speaker = str(item.get("speaker", "")).strip().lower()
                        speaker_label = "Speaker"
                        if raw_speaker.startswith("host"):
                            # Prefer VoiceId first, then Role; both capitalized
                            speaker_label = (
                                f"{str(host_voice).strip().title()} (Host)"
                                if host_voice
                                else "Host"
                            )
                        elif raw_speaker.startswith("guest"):
                            speaker_label = (
                                f"{str(guest_voice).strip().title()} (Guest)"
                                if guest_voice
                                else "Guest"
                            )
                        else:
                            # Fallback to provided speaker label, title-cased
                            speaker_label = item.get("speaker") or "Speaker"
                            speaker_label = str(speaker_label).strip().title()
                        text = str(item.get("text", "")).strip()
                        if text:
                            lines.append(f"**{speaker_label}:** {text}")
                md_conv = "\n\n".join(lines).strip() + "\n"
                return Response(
                    content=md_conv, media_type="text/markdown; charset=utf-8"
                )
        candidate_keys = [
            "revise_pdf_transcripts",
            "revise_transcripts",
            "generate_transcripts",
            "segment_pdf_content",
            "generate_subtitle_transcripts",
        ]
        for key in candidate_keys:
            step = steps.get(key)
            if not step or step.get("status") != "completed":
                continue
            md = step.get("markdown")
            if isinstance(md, str) and md.strip():
                headers = {}
                storage_url = step.get("markdown_storage_url")
                if isinstance(storage_url, str) and storage_url:
                    headers["X-Storage-URL"] = storage_url
                return Response(
                    content=md,
                    media_type="text/markdown; charset=utf-8",
                    headers=headers,
                )
            data = step.get("data") or []
            if isinstance(data, list) and data:
                label = (
                    "Chapter"
                    if key in ("revise_pdf_transcripts", "segment_pdf_content")
                    else "Slide"
                )
                if key in ("revise_pdf_transcripts", "segment_pdf_content"):
                    orig = steps.get("segment_pdf_content", {}).get("data") or []
                    merged: list[dict[str, Any]] = []
                    for i, rev in enumerate(data):
                        base: dict[str, Any] = {"chapter_number": i + 1}
                        if (
                            isinstance(orig, list)
                            and i < len(orig)
                            and isinstance(orig[i], dict)
                        ):
                            for k in ("title", "description", "key_points"):
                                if k in orig[i]:
                                    base[k] = orig[i][k]
                        base["script"] = (
                            rev.get("script", "") if isinstance(rev, dict) else str(rev)
                        )
                        merged.append(base)
                    data_for_md = merged
                else:
                    data_for_md = data
                md_built = transcripts_to_markdown(
                    data_for_md, section_label=label, filename=state.get("filename")
                )
                return Response(
                    content=md_built, media_type="text/markdown; charset=utf-8"
                )

    # Storage fallback
    sp = get_storage_provider()
    # Prefer task-id-based transcript filename first; fall back to file-id if known
    fallback_keys = [
        f"{task_id}_transcript.md",
        f"{task_id}_podcast_transcript.md",  # Podcast-specific transcript
    ]
    if file_id:
        fallback_keys.extend(
            [
                f"{file_id}_transcript.md",
                f"{file_id}_podcast_transcript.md",  # Podcast-specific transcript
            ]
        )
    for key in fallback_keys:
        try:
            if sp.file_exists(key):
                data = sp.download_bytes(key)
                return Response(content=data, media_type="text/markdown; charset=utf-8")
        except Exception:
            continue

    raise HTTPException(status_code=404, detail="Transcript markdown not found")
