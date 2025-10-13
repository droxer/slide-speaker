"""
Shared transcript revision logic for SlideSpeaker pipeline steps.

This module provides common functionality for revising transcripts
in both PDF and presentation slide processing pipelines.
"""

from collections.abc import Callable
from typing import Any

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.storage.paths import output_storage_uri
from slidespeaker.transcript import TranscriptReviewer
from slidespeaker.transcript.markdown import transcripts_to_markdown


async def revise_transcripts_common(
    file_id: str,
    state_key: str,
    get_transcripts_func: Callable[[str], Any],
    language: str = "english",
    task_id: str | None = None,
) -> None:
    """
    Revise transcripts using shared logic.

    Args:
        file_id: Unique identifier for the file
        state_key: State key to update (e.g., "revise_transcripts" or "revise_pdf_transcripts")
        get_transcripts_func: Function to retrieve transcripts data
        language: Target language for revision

    Raises:
        ValueError: If no transcripts data is available
    """
    await state_manager.update_step_status(file_id, state_key, "processing")
    logger.info(f"Starting transcript revision for file: {file_id}")

    # Get transcripts data
    original_transcripts = await get_transcripts_func(file_id)

    if not original_transcripts:
        logger.warning("No transcripts data available for revision")
        await state_manager.update_step_status(file_id, state_key, "completed", [])
        return

    try:
        # Use shared transcript reviewer
        reviewer = TranscriptReviewer()
        revised_transcripts = await reviewer.revise_transcripts(
            original_transcripts, language
        )

        await state_manager.update_step_status(
            file_id, state_key, "completed", revised_transcripts
        )
        # Persist Markdown representation alongside list data without changing the data shape
        try:
            state = await state_manager.get_state(file_id)
            if state and "steps" in state and state_key in state["steps"]:
                # Use label based on whether this is PDF or slides
                label = (
                    "Chapter"
                    if state.get("file_ext", "").lower() == ".pdf"
                    else "Slide"
                )
                # Merge metadata (title/description/key_points) from original transcripts if available
                merged: list[dict[str, Any]] = []
                for i, rev in enumerate(revised_transcripts):
                    base: dict[str, Any] = {}
                    # Attach numbering
                    if label == "Chapter":
                        base["chapter_number"] = i + 1
                    else:
                        base["slide_number"] = i + 1
                    # Pull original fields when present
                    if i < len(original_transcripts):
                        orig = original_transcripts[i] or {}
                        if isinstance(orig, dict):
                            for k in ("title", "description", "key_points"):
                                if k in orig:
                                    base[k] = orig[k]
                    # Use revised script
                    base["script"] = (
                        rev.get("script", "") if isinstance(rev, dict) else str(rev)
                    )
                    merged.append(base)

                md = transcripts_to_markdown(
                    merged, section_label=label, filename=state.get("filename")
                )
                state["steps"][state_key]["markdown"] = md
                await state_manager.save_state(file_id, state)
        except Exception:
            # Non-fatal metadata
            pass

        # Upload final transcript markdown to storage (best-effort)
        try:
            from slidespeaker.configs.config import get_storage_provider

            storage_provider = get_storage_provider()
            state = await state_manager.get_state(file_id)
            _, transcript_key, transcript_uri = output_storage_uri(
                file_id,
                state=state if isinstance(state, dict) else None,
                task_id=task_id,
                segments=("transcripts", "transcript.md"),
            )
            url = storage_provider.upload_bytes(
                md.encode("utf-8"), transcript_key, "text/markdown"
            )
            latest_state = await state_manager.get_state(file_id)
            if (
                latest_state
                and "steps" in latest_state
                and state_key in latest_state["steps"]
            ):
                latest_state["steps"][state_key]["markdown_storage_url"] = url
                latest_state["steps"][state_key]["markdown_storage_key"] = (
                    transcript_key
                )
                latest_state["steps"][state_key]["markdown_storage_uri"] = (
                    transcript_uri
                )
                await state_manager.save_state(file_id, latest_state)
        except Exception as e:
            logger.error(f"Failed to upload transcript markdown to storage: {e}")
        logger.info(
            f"Transcript revision completed successfully with {len(revised_transcripts)} transcripts"
        )
    except Exception as e:
        logger.error(f"Failed to revise transcripts: {e}")
        await state_manager.update_step_status(
            file_id, state_key, "failed", {"error": str(e)}
        )
        raise


async def get_pdf_transcripts_for_revision(file_id: str) -> list[dict[str, Any]]:
    """Get transcripts for PDF revision."""
    state = await state_manager.get_state(file_id)
    chapters: list[dict[str, Any]] = []

    # Use generated PDF chapters for revision
    if (
        state
        and "steps" in state
        and "segment_pdf_content" in state["steps"]
        and "data" in state["steps"]["segment_pdf_content"]
        and state["steps"]["segment_pdf_content"]["data"] is not None
    ):
        chapters = state["steps"]["segment_pdf_content"]["data"]
        logger.info("Using generated PDF chapters for revision")

    return chapters


async def get_slide_transcripts_for_revision(file_id: str) -> list[dict[str, Any]]:
    """Get transcripts for slide revision."""
    state = await state_manager.get_state(file_id)
    transcripts: list[dict[str, Any]] = []

    # Use generated slide transcripts for revision
    if (
        state
        and "steps" in state
        and "generate_transcripts" in state["steps"]
        and "data" in state["steps"]["generate_transcripts"]
        and state["steps"]["generate_transcripts"]["data"] is not None
    ):
        transcripts = state["steps"]["generate_transcripts"]["data"]
        logger.info("Using generated slide transcripts for revision")

    return transcripts
