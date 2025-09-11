"""
Transcript routes for serving final revised Markdown transcripts.

Exposes an endpoint to retrieve the final (revised) transcript in Markdown
for both PDF and slide pipelines. Falls back to generating Markdown from
the revised transcript list if the pre-rendered Markdown is not present.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Response

from slidespeaker.core.state_manager import state_manager
from slidespeaker.transcript.markdown import transcripts_to_markdown

router = APIRouter(prefix="/api", tags=["transcripts"])


@router.get("/transcripts/{file_id}/markdown")
async def get_final_markdown_transcript(file_id: str) -> Response:
    """Return the final revised transcript as Markdown.

    Prefers the revised transcripts step:
      - PDF:   steps.revise_pdf_transcripts
      - Slides: steps.revise_transcripts

    If a pre-rendered Markdown field is present, it is returned. Otherwise,
    Markdown is generated on the fly from the revised transcripts list.
    """
    state = await state_manager.get_state(file_id)
    if not state or "steps" not in state:
        raise HTTPException(status_code=404, detail="State not found")

    steps = state["steps"]
    # Prefer PDF revised when present; otherwise slide revised
    candidate_keys = ["revise_pdf_transcripts", "revise_transcripts"]

    for key in candidate_keys:
        step = steps.get(key)
        if not step or step.get("status") != "completed":
            continue

        # Pre-rendered Markdown available
        md = step.get("markdown")
        if isinstance(md, str) and md.strip():
            # Attach storage URL in header if present
            headers = {}
            storage_url = step.get("markdown_storage_url")
            if isinstance(storage_url, str) and storage_url:
                headers["X-Storage-URL"] = storage_url
            return Response(
                content=md, media_type="text/markdown; charset=utf-8", headers=headers
            )

        # Fallback: build Markdown from data
        data = step.get("data") or []
        if isinstance(data, list) and data:
            label = "Chapter" if key == "revise_pdf_transcripts" else "Slide"
            # If PDF, enrich with title/description/key_points from original segmentation when available
            if key == "revise_pdf_transcripts":
                orig = steps.get("segment_pdf_content", {}).get("data") or []
                merged: list[dict[str, Any]] = []
                for i, rev in enumerate(data):
                    base: dict[str, Any] = {}
                    base["chapter_number"] = i + 1
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
            return Response(content=md_built, media_type="text/markdown; charset=utf-8")

    raise HTTPException(status_code=404, detail="Revised transcripts not found")


@router.get("/tasks/{task_id}/transcripts/markdown")
async def get_final_markdown_transcript_by_task(task_id: str) -> Response:
    """Task-based transcript endpoint that resolves file_id from task_id."""
    from slidespeaker.core.task_queue import task_queue

    task = await task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    file_id = (task.get("kwargs") or {}).get("file_id") or task.get("file_id")
    if not file_id:
        raise HTTPException(status_code=404, detail="File not found for task")
    return await get_final_markdown_transcript(file_id)
