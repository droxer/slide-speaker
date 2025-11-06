"""
Podcast pipeline coordinator (from PDF sources).

Generates a two-person conversation podcast based on PDF chapter segmentation.
"""

import json
from contextlib import suppress
from pathlib import Path
from typing import Any

from loguru import logger

from slidespeaker.core.state_manager import state_manager

from ..base import BasePipeline
from ..steps.podcast.pdf import (
    compose_podcast_step,
    generate_podcast_audio_step,
    generate_podcast_script_step,
    generate_podcast_subtitles_step,
    translate_podcast_script_step,
)
from ..steps.video.pdf import segment_content_step as pdf_segment_content_step


def _podcast_steps(
    target_transcript_language: str | None, fallback_voice_language: str
) -> list[str]:
    """Determine ordered steps for podcast pipeline.

    Always generate the script in English first. Include a translation step when the
    desired transcript language differs from English. Then generate the audio using
    the voice language and compose.
    """
    steps: list[str] = ["generate_podcast_script"]
    target = (
        target_transcript_language or fallback_voice_language or "english"
    ).lower()

    if target != "english":
        steps.append("translate_podcast_script")

    steps.extend(
        ["generate_podcast_audio", "generate_podcast_subtitles", "compose_podcast"]
    )
    return steps


def _podcast_step_name(step: str) -> str:
    """Get display name for podcast steps."""
    base = {
        "generate_podcast_script": "Generating podcast script (two speakers)",
        "translate_podcast_script": "Translating podcast script",
        "generate_podcast_audio": "Generating podcast audio",
        "generate_podcast_subtitles": "Creating podcast subtitles",
        "compose_podcast": "Composing final podcast (MP3)",
    }
    return base.get(step, step)


def extract_podcast_dialogue_from_state(
    state: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Return sanitized podcast dialogue metadata from pipeline state."""
    if not state or "steps" not in state:
        return None

    steps = state["steps"]
    host_voice = None
    guest_voice = None
    target_language = (
        state.get("podcast_transcript_language")
        or state.get("voice_language")
        or "english"
    )

    # Try to get dialogue from audio generation step first
    audio_data = _get_audio_dialogue_data(steps)
    if audio_data:
        return audio_data

    # Fallback to translated script or original English script
    return _get_script_dialogue_data(steps, target_language, host_voice, guest_voice)


def _get_audio_dialogue_data(steps: dict[str, Any]) -> dict[str, Any] | None:
    """Extract dialogue from audio generation step."""
    try:
        ga = steps.get("generate_podcast_audio") or {}
        if ga.get("status") != "completed":
            return None

        ga_data = ga.get("data") or {}
        host_voice = ga_data.get("host_voice")
        guest_voice = ga_data.get("guest_voice")

        # Get dialogue from either 'dialogue' or 'segment_metadata' field
        dlg = ga_data.get("dialogue")
        if not dlg and isinstance(ga_data.get("segment_metadata"), list):
            dlg = ga_data["segment_metadata"]

        if not dlg:
            return None

        dialogue_language = ga_data.get("dialogue_language", "english")
        total_duration = max(float(ga_data.get("total_duration", 0)), 0.0)

        return {
            "dialogue": dlg,
            "host_voice": host_voice,
            "guest_voice": guest_voice,
            "language": dialogue_language,
            "source": "generate_podcast_audio",
            "total_duration": total_duration,
        }
    except Exception:
        return None


def _get_script_dialogue_data(
    steps: dict[str, Any],
    target_language: str,
    host_voice: str | None,
    guest_voice: str | None,
) -> dict[str, Any] | None:
    """Extract dialogue from script steps as fallback."""
    # Check translated script first
    translated = steps.get("translate_podcast_script")
    if isinstance(translated, dict) and translated.get("status") == "completed":
        dialogue_data = translated.get("data", [])
        return {
            "dialogue": dialogue_data,
            "host_voice": host_voice,
            "guest_voice": guest_voice,
            "language": target_language,
            "source": "translate_podcast_script",
            "total_duration": None,
        }

    # Check original English script
    original = steps.get("generate_podcast_script")
    if isinstance(original, dict) and original.get("status") == "completed":
        dialogue_data = original.get("data", [])
        return {
            "dialogue": dialogue_data,
            "host_voice": host_voice,
            "guest_voice": guest_voice,
            "language": "english",
            "source": "generate_podcast_script",
            "total_duration": None,
        }

    return None


async def _save_podcast_transcript_to_storage(
    file_id: str, task_id: str | None = None
) -> None:
    """Save podcast transcript to storage with task_id naming."""
    logger.info(f"Saving podcast transcript to storage for file: {file_id}")

    from slidespeaker.configs.config import get_storage_provider

    state = await state_manager.get_state(file_id)
    if not state:
        return

    script_payload = extract_podcast_dialogue_from_state(state)
    if not script_payload:
        logger.debug(f"No podcast content to save for file: {file_id}")
        return

    storage_provider = get_storage_provider()
    base_id = task_id if isinstance(task_id, str) and task_id else file_id

    # Get subtitle file paths
    vtt_local_path, srt_local_path = _get_subtitle_paths(state)

    # Upload main script
    script_url = _upload_podcast_script(storage_provider, script_payload, base_id)

    # Upload VTT if needed
    vtt_url = _upload_podcast_vtt_if_needed(storage_provider, vtt_local_path, base_id)

    # Update state with URLs
    await _update_state_with_urls(file_id, script_url, vtt_url, srt_local_path)


def _get_subtitle_paths(state: dict[str, Any]) -> tuple[str | None, str | None]:
    """Extract subtitle file paths from state."""
    subtitles_step = state.get("steps", {}).get("generate_podcast_subtitles") or {}
    subtitles_data = subtitles_step.get("data") or {}

    vtt_local_path = None
    srt_local_path = None

    for candidate in subtitles_data.get("subtitle_files", []):
        if isinstance(candidate, str):
            if candidate.endswith(".vtt") and not vtt_local_path:
                vtt_local_path = candidate
            elif candidate.endswith(".srt") and not srt_local_path:
                srt_local_path = candidate

    return vtt_local_path, srt_local_path


def _upload_podcast_script(
    storage_provider, script_payload: dict, base_id: str
) -> str | None:
    """Upload the main podcast script JSON file."""
    script_key = f"{base_id}_podcast_script.json"
    script_bytes = json.dumps(
        script_payload, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return storage_provider.upload_bytes(script_bytes, script_key, "application/json")


def _upload_podcast_vtt_if_needed(
    storage_provider, vtt_local_path: str | None, base_id: str
) -> str | None:
    """Upload VTT file if needed."""
    if not vtt_local_path:
        return None

    try:
        vtt_key = f"{base_id}_podcast_transcript.vtt"
        return storage_provider.upload_file(str(vtt_local_path), vtt_key, "text/vtt")
    except Exception as exc:
        logger.error(f"Failed to upload podcast VTT: {exc}")
        return None


async def _update_state_with_urls(
    file_id: str,
    script_url: str | None,
    vtt_url: str | None,
    srt_local_path: str | None,
) -> None:
    """Update state with URLs to the uploaded files."""
    state = await state_manager.get_state(file_id)
    if not state or "steps" not in state:
        return

    steps = state["steps"]
    pod_step = steps.get("generate_podcast_script") or {}
    audio_step = steps.get("generate_podcast_audio") or {}

    # Update podcast script step with URLs
    if script_url:
        pod_step["script_storage_url"] = script_url
    if vtt_url:
        pod_step["vtt_storage_url"] = vtt_url

    # Update audio step with URLs and subtitle info
    audio_data = audio_step.get("data") or {}
    if script_url:
        audio_data["script_storage_url"] = script_url
    if vtt_url:
        audio_data["vtt_storage_url"] = vtt_url

    # Add subtitle paths to data
    subtitles_payload = audio_data.get("subtitles") or {}
    if vtt_url:
        subtitles_payload["vtt"] = vtt_url
    if srt_local_path:
        subtitles_payload["srt"] = srt_local_path
    audio_data["subtitles"] = subtitles_payload

    audio_step["data"] = audio_data

    # Save updated steps back to state
    if pod_step:
        steps["generate_podcast_script"] = pod_step
    if audio_step:
        steps["generate_podcast_audio"] = audio_step

    await state_manager.save_state(file_id, state)


async def from_pdf(
    file_id: str,
    file_path: Path,
    voice_language: str = "english",
    transcript_language: str | None = None,
    task_id: str | None = None,
) -> None:
    pipeline = PodcastPipeline(
        file_id=file_id,
        file_path=file_path,
        task_id=task_id,
        voice_language=voice_language,
        transcript_language=transcript_language,
    )
    await pipeline.execute_pipeline()


class PodcastPipeline(BasePipeline):
    """Podcast Pipeline Implementation."""

    def __init__(
        self,
        file_id: str,
        file_path: Path,
        task_id: str | None = None,
        voice_language: str = "english",
        transcript_language: str | None = None,
    ):
        super().__init__(file_id, file_path, task_id)
        self.voice_language = voice_language
        self.transcript_language = transcript_language

    def get_step_display_name(self, step_name: str) -> str:
        return _podcast_step_name(step_name)

    async def execute_pipeline(self) -> None:
        logger.info(f"Starting podcast generation (PDF) for file {self.file_id}")

        if not await self._check_and_handle_prerequisites():
            return

        # Ensure base state exists (accept_task should have created it)
        st = await state_manager.get_state(self.file_id)
        if st:
            st["generate_podcast"] = True
            st["voice_language"] = self.voice_language
            if self.transcript_language:
                st["podcast_transcript_language"] = self.transcript_language
            await state_manager.save_state(self.file_id, st)

        # Ensure prerequisite PDF segmentation exists for podcast-only runs
        try:
            st_now = await state_manager.get_state(self.file_id)
            needs_segment = True
            if st_now and (steps := st_now.get("steps")):
                seg = (
                    steps.get("segment_pdf_content")
                    if isinstance(steps, dict)
                    else None
                )
                if (
                    seg
                    and isinstance(seg, dict)
                    and seg.get("status") == "completed"
                    and seg.get("data")
                ):
                    needs_segment = False
            if needs_segment:
                await pdf_segment_content_step(self.file_id, self.file_path, "english")
        except Exception as e:
            logger.error(f"Prerequisite PDF segmentation failed for podcast: {e}")
            await state_manager.add_error(self.file_id, str(e), "segment_pdf_content")
            await state_manager.mark_failed(self.file_id)
            raise

        steps_order = _podcast_steps(self.transcript_language, self.voice_language)
        logger.info(f"Podcast steps order: {steps_order}")
        logger.info(
            f"transcript_language: {self.transcript_language}, voice_language: {self.voice_language}"
        )

        try:
            for step_name in steps_order:
                success = await self._execute_step(
                    step_name, self._execute_podcast_step, step_name
                )
                if not success:
                    return

            # Save podcast transcript to storage
            logger.info(
                f"Calling _save_podcast_transcript_to_storage with file_id: {self.file_id}, task_id: {self.task_id}"
            )
            await _save_podcast_transcript_to_storage(self.file_id, self.task_id)

            # Mark overall processing as completed for podcast-only or combined runs
            with suppress(Exception):
                await state_manager.mark_completed(self.file_id)
            logger.info(
                f"All podcast processing steps completed for file {self.file_id}"
            )
        except Exception as e:
            logger.error(f"Podcast processing failed: {e}")
            await state_manager.mark_failed(self.file_id)
            raise

    async def _execute_podcast_step(self, step_name: str):
        """Execute a specific podcast processing step."""
        if step_name == "generate_podcast_script":
            await generate_podcast_script_step(self.file_id, "english")
        elif step_name == "translate_podcast_script":
            await translate_podcast_script_step(
                self.file_id,
                source_language="english",
                target_language=(self.transcript_language or self.voice_language),
            )
        elif step_name == "generate_podcast_audio":
            await generate_podcast_audio_step(self.file_id, self.voice_language)
        elif step_name == "generate_podcast_subtitles":
            await generate_podcast_subtitles_step(self.file_id)
        elif step_name == "compose_podcast":
            await compose_podcast_step(self.file_id)
