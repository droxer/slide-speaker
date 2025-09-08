"""
PDF subtitle generation step for SlideSpeaker.

This module handles the generation of subtitles for PDF chapters.
"""

from pathlib import Path
from typing import Any

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.processing.subtitle_generator import SubtitleGenerator
from slidespeaker.utils.config import get_storage_provider
from slidespeaker.utils.locales import locale_utils

subtitle_generator = SubtitleGenerator()

# Get storage provider instance
storage_provider = get_storage_provider()


async def generate_subtitles_step(file_id: str, language: str = "english") -> None:
    """
    Generate subtitles for PDF chapters.

    Args:
        file_id: Unique identifier for the file
        language: Language for subtitle generation
    """
    await state_manager.update_step_status(
        file_id, "generate_pdf_subtitles", "processing"
    )
    logger.info(f"Generating subtitles for PDF chapters for file: {file_id}")

    try:
        # Get chapters from state
        state = await state_manager.get_state(file_id)
        chapters: list[dict[str, Any]] = []
        if (
            state
            and "steps" in state
            and "segment_pdf_content" in state["steps"]
            and state["steps"]["segment_pdf_content"]["data"] is not None
        ):
            chapters = state["steps"]["segment_pdf_content"]["data"]

        if not chapters:
            raise ValueError("No chapter data available for subtitle generation")

        # Create working directory
        work_dir = Path("output") / file_id
        subtitle_dir = work_dir / "subtitles"
        subtitle_dir.mkdir(exist_ok=True, parents=True)

        # Generate subtitles for each chapter
        subtitle_storage_urls = []
        subtitle_local_paths = []
        for i, chapter in enumerate(chapters):
            script = chapter.get("script", "")
            if script:
                subtitle_path = subtitle_dir / f"chapter_{i + 1}"
                (
                    srt_path,
                    vtt_path,
                ) = await subtitle_generator.generate_subtitles_for_text(
                    script,
                    5.0,
                    subtitle_path,
                    language,  # Default duration of 5 seconds
                )

                # Add local paths for subsequent processing (do not upload to storage)
                subtitle_local_paths.extend([srt_path, vtt_path])

                # Note: Individual chapter subtitles are kept as local files only
                # Only final combined subtitles will be uploaded to storage

        # Combine all chapter subtitles into final subtitle files
        if subtitle_local_paths:
            # Separate SRT and VTT files
            srt_files = [Path(p) for p in subtitle_local_paths if p.endswith(".srt")]
            vtt_files = [Path(p) for p in subtitle_local_paths if p.endswith(".vtt")]

            # Create final combined subtitle files with locale-aware naming
            work_dir = Path("output") / file_id
            locale_code = locale_utils.get_locale_code(language)
            final_srt_path = work_dir / f"{file_id}_final_{locale_code}.srt"
            final_vtt_path = work_dir / f"{file_id}_final_{locale_code}.vtt"

            # Combine SRT files
            if srt_files:
                final_srt_file = subtitle_generator.combine_srt_files(
                    srt_files, final_srt_path
                )
                logger.info(f"Combined SRT files into final subtitle: {final_srt_file}")

                # Upload final SRT to storage
                try:
                    srt_key = f"{file_id}_final_{locale_code}.srt"
                    srt_url = storage_provider.upload_file(
                        final_srt_file, srt_key, "text/plain"
                    )
                    subtitle_storage_urls.append(srt_url)
                    logger.info(f"Uploaded final SRT subtitle to storage: {srt_url}")
                except Exception as e:
                    logger.error(f"Failed to upload final SRT subtitle to storage: {e}")
                    # Fallback to local path if storage upload fails
                    subtitle_storage_urls.append(final_srt_file)

            # Combine VTT files
            if vtt_files:
                final_vtt_file = subtitle_generator.combine_vtt_files(
                    vtt_files, final_vtt_path
                )
                logger.info(f"Combined VTT files into final subtitle: {final_vtt_file}")

                # Upload final VTT to storage
                try:
                    vtt_key = f"{file_id}_final_{locale_code}.vtt"
                    vtt_url = storage_provider.upload_file(
                        final_vtt_file, vtt_key, "text/vtt"
                    )
                    subtitle_storage_urls.append(vtt_url)
                    logger.info(f"Uploaded final VTT subtitle to storage: {vtt_url}")
                except Exception as e:
                    logger.error(f"Failed to upload final VTT subtitle to storage: {e}")
                    # Fallback to local path if storage upload fails
                    subtitle_storage_urls.append(final_vtt_file)

            # Update local paths to include final combined subtitles
            final_local_paths = []
            if srt_files:
                final_local_paths.append(final_srt_file)
            if vtt_files:
                final_local_paths.append(final_vtt_file)
        else:
            final_local_paths = []

        # Store both local paths (for subsequent processing) and storage URLs (for reference)
        # Only final combined subtitles are uploaded to storage
        all_local_paths = subtitle_local_paths + final_local_paths
        storage_data = {
            "local_paths": all_local_paths,
            "storage_urls": subtitle_storage_urls,  # This will only contain final subtitle URLs
            "final_subtitles": {
                "local_paths": final_local_paths,
                "storage_urls": subtitle_storage_urls,  # Same as above - only final subtitles
            }
            if final_local_paths
            else {},
        }

        # Store subtitle data in state
        await state_manager.update_step_status(
            file_id, "generate_pdf_subtitles", "completed", storage_data
        )

        logger.info(
            f"Generated {len(subtitle_local_paths)} chapter subtitle files and "
            f"combined them into final subtitles for file: {file_id}"
        )

    except Exception as e:
        logger.error(f"Failed to generate PDF subtitles for file {file_id}: {e}")
        raise
