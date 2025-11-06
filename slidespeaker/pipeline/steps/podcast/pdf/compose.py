"""
Compose final podcast MP3 by concatenating generated segments.

Uses ffmpeg concat demuxer and uploads the result with task-first naming if available.
"""

import os
import subprocess
from contextlib import suppress
from pathlib import Path

from loguru import logger

from slidespeaker.configs.config import config, get_storage_provider
from slidespeaker.core.state_manager import state_manager
from slidespeaker.storage.paths import output_storage_uri


def _concat_with_ffmpeg(inputs: list[str], output_mp3: str) -> bool:
    if not inputs:
        return False
    list_file = Path(output_mp3).with_suffix(".txt")
    try:
        with open(list_file, "w", encoding="utf-8") as f:
            for p in inputs:
                f.write(f"file '{p}'\n")
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            output_mp3,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            logger.error(f"ffmpeg concat failed: {res.stderr[:400]}")
            return False
        return os.path.exists(output_mp3) and os.path.getsize(output_mp3) > 0
    finally:
        with suppress(Exception):
            list_file.unlink(missing_ok=True)


async def compose_podcast_step(file_id: str) -> None:
    await state_manager.update_step_status(file_id, "compose_podcast", "processing")
    logger.info(f"Composing final podcast for file {file_id}")

    try:
        st = await state_manager.get_state(file_id)
        segments: list[str] = []
        if st and st.get("steps") and st["steps"].get("generate_podcast_audio"):
            data = st["steps"]["generate_podcast_audio"].get("data") or {}
            if isinstance(data, dict):
                segments = list(data.get("segments") or [])

        if not segments:
            logger.warning("No podcast segments; composing empty output")
            await state_manager.update_step_status(
                file_id, "compose_podcast", "completed", {"podcast_file": None}
            )
            return

        base_id, storage_key, storage_uri = output_storage_uri(
            file_id,
            state=st if isinstance(st, dict) else None,
            segments=("podcast", "final.mp3"),
        )
        podcast_dir = config.output_dir / "/".join(storage_key.split("/")[:-1])
        podcast_dir.mkdir(parents=True, exist_ok=True)
        podcast_path = config.output_dir / storage_key

        ok = _concat_with_ffmpeg(segments, str(podcast_path))
        if not ok:
            await state_manager.update_step_status(
                file_id, "compose_podcast", "failed", {"error": "concat_failed"}
            )
            raise RuntimeError("Podcast composition failed")

        # Upload to storage (using same base_id as local file)
        url = None
        sp = get_storage_provider()
        try:
            url = sp.upload_file(str(podcast_path), storage_key, "audio/mpeg")
        except Exception as e:  # noqa: BLE001 - propagate non-local failures
            logger.error(f"Podcast upload failed: {e}")
            if config.storage_provider != "local":
                await state_manager.update_step_status(
                    file_id,
                    "compose_podcast",
                    "failed",
                    {
                        "error": "podcast_upload_failed",
                        "detail": str(e),
                        "storage_key": storage_key,
                    },
                )
                raise
            logger.warning(
                "Continuing with local podcast artifact because storage provider is local."
            )

        await state_manager.update_step_status(
            file_id,
            "compose_podcast",
            "completed",
            {
                "podcast_file": str(podcast_path),
                "storage_url": url,
                "storage_key": storage_key,
                "storage_uri": storage_uri,
            },
        )

        latest_state = await state_manager.get_state(file_id)
        if latest_state and isinstance(latest_state, dict):
            artifacts = dict(latest_state.get("artifacts") or {})
            artifacts["podcast_audio"] = {
                "local_path": str(podcast_path),
                "storage_key": storage_key,
                "storage_uri": storage_uri,
                "content_type": "audio/mpeg",
            }
            latest_state["artifacts"] = artifacts
            await state_manager.save_state(file_id, latest_state)

    except Exception as e:
        logger.error(f"Failed to compose podcast for {file_id}: {e}")
        await state_manager.update_step_status(
            file_id,
            "compose_podcast",
            "failed",
            {
                "error": "podcast_composition_failed",
                "detail": str(e),
            },
        )
        raise
