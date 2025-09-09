"""
Generate audio step for the presentation pipeline.

This module generates text-to-speech audio files from the reviewed transcripts.
It uses configurable TTS services (OpenAI, ElevenLabs) to create natural-sounding
voice audio for each slide in the presentation.
"""

from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.services.tts_factory import TTSFactory
from slidespeaker.utils.config import config, get_storage_provider

# Get storage provider instance
storage_provider = get_storage_provider()


async def generate_audio_step(file_id: str, language: str = "english") -> None:
    """
    Generate audio from transcripts using TTS services.

    This function converts the reviewed presentation transcripts into audio files
    using text-to-speech technology. It supports multiple TTS providers through
    a factory pattern and includes error handling for individual slide processing.
    The function includes periodic cancellation checks for responsive task management.
    """
    await state_manager.update_step_status(file_id, "generate_audio", "processing")
    logger.info(f"Starting audio generation for file: {file_id}")
    state = await state_manager.get_state(file_id)

    # Check for task cancellation before starting
    if state and state.get("task_id"):
        from slidespeaker.core.task_queue import task_queue

        if await task_queue.is_task_cancelled(state["task_id"]):
            logger.info(
                f"Task {state['task_id']} was cancelled during audio generation"
            )
            await state_manager.mark_cancelled(file_id, cancelled_step="generate_audio")
            return

    # Comprehensive null checking for transcripts data
    # Check for translated transcripts first, then fall back to reviewed English transcripts
    transcripts = []

    # Check for translated voice transcripts first (for non-English audio)
    if (
        state
        and "steps" in state
        and "translate_voice_transcripts" in state["steps"]
        and state["steps"]["translate_voice_transcripts"]["data"] is not None
        and state["steps"]["translate_voice_transcripts"].get("status") == "completed"
    ):
        transcripts = state["steps"]["translate_voice_transcripts"]["data"]
        logger.info("Using translated voice transcripts for audio generation")
    # Fall back to revised English transcripts
    elif (
        state
        and "steps" in state
        and "revise_transcripts" in state["steps"]
        and state["steps"]["revise_transcripts"]["data"] is not None
    ):
        transcripts = state["steps"]["revise_transcripts"]["data"]
        logger.info("Using revised English transcripts for audio generation")

    if not transcripts:
        raise ValueError("No transcripts data available for audio generation")

    # Prepare intermediate audio directory: output/{file_id}/audio
    audio_dir = config.output_dir / file_id / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    audio_files = []
    for i, transcript_data in enumerate(transcripts):
        # Check for task cancellation periodically
        if i % 2 == 0 and state and state.get("task_id"):  # Check every 2 slides
            from slidespeaker.core.task_queue import task_queue

            if await task_queue.is_task_cancelled(state["task_id"]):
                logger.info(
                    f"Task {state['task_id']} was cancelled during audio generation"
                )
                await state_manager.mark_cancelled(
                    file_id, cancelled_step="generate_audio"
                )
                return

        # Additional null check for individual transcript data
        if (
            transcript_data
            and "script" in transcript_data
            and transcript_data["script"]
        ):
            script_text = transcript_data["script"].strip()
            if script_text:  # Only generate audio if transcript is not empty
                audio_path = audio_dir / f"slide_{i + 1}.mp3"
                try:
                    # Create TTS service using factory
                    tts_service = TTSFactory.create_service()

                    # Get supported voices for language
                    voices = tts_service.get_supported_voices(language)
                    voice = voices[0] if voices else None

                    await tts_service.generate_speech(
                        script_text, audio_path, language=language, voice=voice
                    )

                    # Determine audio duration using ffprobe
                    try:
                        import json
                        import subprocess

                        cmd = [
                            "ffprobe",
                            "-v",
                            "quiet",
                            "-print_format",
                            "json",
                            "-show_format",
                            "-show_streams",
                            str(audio_path),
                        ]
                        result = subprocess.run(
                            cmd, capture_output=True, text=True, timeout=10
                        )
                        if result.returncode == 0 and result.stdout.strip():
                            data = json.loads(result.stdout)
                            # Try to get duration from format first
                            if "format" in data and "duration" in data["format"]:
                                duration = float(data["format"]["duration"])
                                logger.info(
                                    f"Determined duration for slide {i + 1}: {duration} seconds"
                                )
                            # If not in format, check streams
                            elif "streams" in data:
                                for stream in data["streams"]:
                                    if "duration" in stream:
                                        duration = float(stream["duration"])
                                        logger.info(
                                            f"Determined duration for slide {i + 1}: {duration} seconds"
                                        )
                                        break
                    except Exception as e:
                        logger.warning(
                            f"Could not determine duration for slide {i + 1}: {e}"
                        )

                    # Keep audio files local - only final files should be uploaded to cloud storage
                    audio_files.append(str(audio_path))
                    logger.info(f"Generated audio for slide {i + 1}: {audio_path}")

                except Exception as e:
                    logger.error(f"Failed to generate audio for slide {i + 1}: {e}")
                    raise
            else:
                logger.warning(
                    f"Skipping audio generation for slide {i + 1} due to empty transcript"
                )
        else:
            logger.warning(
                f"Skipping audio generation for slide {i + 1} due to "
                f"missing or empty transcript data"
            )

    await state_manager.update_step_status(
        file_id, "generate_audio", "completed", audio_files
    )
    logger.info(
        f"Stage 'Synthesizing voice audio' completed successfully with "
        f"{len(audio_files)} audio files"
    )

    # Verify state was updated
    updated_state = await state_manager.get_state(file_id)
    if (
        updated_state
        and updated_state["steps"]["generate_audio"]["status"] == "completed"
    ):
        logger.info(f"Successfully updated generate_audio to completed for {file_id}")
        logger.info(f"Audio files: {audio_files}")
    else:
        logger.error(f"Failed to update generate_audio state for {file_id}")
