"""
PDF subtitle generation step for SlideSpeaker.

This module handles the generation of subtitles for PDF chapters using transcripts.
"""

from pathlib import Path
from typing import Any

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.processing.subtitle_generator import SubtitleGenerator
from slidespeaker.utils.config import config, get_storage_provider
from slidespeaker.utils.locales import locale_utils

subtitle_generator = SubtitleGenerator()

# Resolve storage provider at upload time to reflect current config


async def generate_subtitles_step(file_id: str, language: str = "english") -> None:
    """
    Generate subtitles for PDF chapters using transcripts.

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

        # Determine which transcripts to use for subtitles
        chapters = []
        if state and "steps" in state:
            # Priority 1: Use translated subtitle transcripts if available
            if (
                "translate_subtitle_transcripts" in state["steps"]
                and state["steps"]["translate_subtitle_transcripts"]["data"] is not None
                and state["steps"]["translate_subtitle_transcripts"].get("status")
                == "completed"
            ):
                translated_transcripts = state["steps"][
                    "translate_subtitle_transcripts"
                ]["data"]
                # Get original chapters and update with translated transcripts
                if (
                    "segment_pdf_content" in state["steps"]
                    and state["steps"]["segment_pdf_content"]["data"] is not None
                ):
                    original_chapters = state["steps"]["segment_pdf_content"]["data"]
                    for i, chapter in enumerate(original_chapters):
                        updated_chapter = chapter.copy()
                        if i < len(translated_transcripts):
                            updated_chapter["script"] = translated_transcripts[i].get(
                                "script", chapter.get("script", "")
                            )
                        chapters.append(updated_chapter)
                logger.info(
                    "Using translated subtitle transcripts for PDF subtitle generation"
                )

            # Priority 2: Use translated voice transcripts as fallback
            elif (
                "translate_voice_transcripts" in state["steps"]
                and state["steps"]["translate_voice_transcripts"]["data"] is not None
                and state["steps"]["translate_voice_transcripts"].get("status")
                == "completed"
            ):
                translated_transcripts = state["steps"]["translate_voice_transcripts"][
                    "data"
                ]
                # Get original chapters and update with translated transcripts
                if (
                    "segment_pdf_content" in state["steps"]
                    and state["steps"]["segment_pdf_content"]["data"] is not None
                ):
                    original_chapters = state["steps"]["segment_pdf_content"]["data"]
                    for i, chapter in enumerate(original_chapters):
                        updated_chapter = chapter.copy()
                        if i < len(translated_transcripts):
                            updated_chapter["script"] = translated_transcripts[i].get(
                                "script", chapter.get("script", "")
                            )
                        chapters.append(updated_chapter)
                logger.info(
                    "Using translated voice transcripts for PDF subtitle generation"
                )

            # Priority 3: Fall back to original chapters with English transcripts
            elif (
                "segment_pdf_content" in state["steps"]
                and state["steps"]["segment_pdf_content"]["data"] is not None
            ):
                chapters = state["steps"]["segment_pdf_content"]["data"]
                logger.info(
                    "Using original English transcripts for PDF subtitle generation"
                )

        if not chapters:
            raise ValueError("No chapter data available for subtitle generation")

        # Create working directory under configured output dir
        work_dir = config.output_dir / file_id
        subtitle_dir = work_dir / "subtitles"
        subtitle_dir.mkdir(exist_ok=True, parents=True)

        # Initialize variables for storing subtitle paths
        subtitle_storage_urls = []
        final_local_paths = []

        # Get audio files for timing if available
        audio_files_data = []
        if (
            state
            and "steps" in state
            and "generate_pdf_audio" in state["steps"]
            and state["steps"]["generate_pdf_audio"]["data"] is not None
        ):
            audio_data = state["steps"]["generate_pdf_audio"]["data"]
            # Extract local paths from the stored data
            if isinstance(audio_data, dict) and "local_paths" in audio_data:
                audio_files_data = audio_data["local_paths"]
            else:
                # Fallback for old format or unexpected data structure
                audio_files_data = audio_data if isinstance(audio_data, list) else []

        # Convert to Path objects
        audio_files = [Path(p) for p in audio_files_data] if audio_files_data else []

        # Generate subtitles using the main generate_subtitles method for proper audio sync
        if chapters and audio_files and len(chapters) == len(audio_files):
            # Use the proper generate_subtitles method that syncs with audio files
            # Write into intermediate subtitles folder for debugging
            locale_code = locale_utils.get_locale_code(language)
            video_path = subtitle_dir / f"{file_id}_subtitles_{locale_code}.mp4"
            logger.info(
                f"Starting subtitle generation for {file_id} with {len(chapters)} chapters"
            )
            logger.info(f"Video path: {video_path}")
            logger.info(f"Language: {language}")

            srt_path, vtt_path = subtitle_generator.generate_subtitles(
                chapters, audio_files, video_path, language
            )

            logger.info(
                f"Completed subtitle generation for {file_id} - SRT: {srt_path}, VTT: {vtt_path}"
            )

            # These are the final subtitle files, no need to combine
            subtitle_local_paths = [srt_path, vtt_path]

            # Upload final subtitles to storage
            locale_code = locale_utils.get_locale_code(language)
            logger.info(f"About to upload subtitles to storage - locale: {locale_code}")

            # Upload final SRT to storage
            storage_provider = get_storage_provider()
            try:
                srt_key = f"{file_id}_final_{locale_code}.srt"
                logger.info(f"Uploading SRT file: {srt_path} with key: {srt_key}")
                srt_url = storage_provider.upload_file(srt_path, srt_key, "text/plain")
                subtitle_storage_urls.append(srt_url)
                logger.info(f"Uploaded final SRT subtitle to storage: {srt_url}")
            except Exception as e:
                logger.error(f"Failed to upload final SRT subtitle to storage: {e}")
                # Fallback to local path if storage upload fails
                subtitle_storage_urls.append(srt_path)

            # Upload final VTT to storage
            try:
                vtt_key = f"{file_id}_final_{locale_code}.vtt"
                logger.info(f"Uploading VTT file: {vtt_path} with key: {vtt_key}")
                vtt_url = storage_provider.upload_file(vtt_path, vtt_key, "text/vtt")
                subtitle_storage_urls.append(vtt_url)
                logger.info(f"Uploaded final VTT subtitle to storage: {vtt_url}")
            except Exception as e:
                logger.error(f"Failed to upload final VTT subtitle to storage: {e}")
                # Fallback to local path if storage upload fails
                subtitle_storage_urls.append(vtt_path)

            logger.info(
                f"Completed subtitle storage uploads - {len(subtitle_storage_urls)} URLs"
            )

            # Set final local paths to the same files
            final_local_paths = [srt_path, vtt_path]
        else:
            # If audio files are not available, we cannot generate meaningful subtitles
            # This would result in incorrect timing that doesn't match the final video
            # Fail fast and raise an exception to prevent incorrect video generation
            error_msg = (
                f"Cannot generate subtitles for file {file_id} - audio files not available. "
                f"Chapters: {len(chapters)}, Audio files: {len(audio_files)}. "
                f"Subtitle generation requires properly generated audio files for synchronization."
            )
            logger.error(error_msg)

            # Log additional details for debugging
            if chapters and (not audio_files or len(chapters) != len(audio_files)):
                logger.error(
                    f"Subtitle generation failed for file {file_id} due to missing or mismatched audio files. "
                    f"This indicates a problem in the processing pipeline where audio generation failed "
                    f"but subtitle generation was still attempted."
                )

            # Raise exception to stop processing and alert the system
            raise ValueError(error_msg)

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

        logger.info(f"About to update state with subtitle data for file: {file_id}")
        # Store subtitle data in state
        await state_manager.update_step_status(
            file_id, "generate_pdf_subtitles", "completed", storage_data
        )

        logger.info(
            f"Generated subtitles for file: {file_id} "
            f"(final subtitles: {len(final_local_paths)}, total files: {len(subtitle_local_paths)})"
        )
        logger.info(
            f"PDF subtitle generation completed successfully for file: {file_id}"
        )

    except Exception as e:
        logger.error(f"Failed to generate PDF subtitles for file {file_id}: {e}")
        raise
