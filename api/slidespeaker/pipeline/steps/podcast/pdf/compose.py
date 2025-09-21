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

    out_dir = config.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    podcast_path = out_dir / f"{file_id}_podcast.mp3"

    ok = _concat_with_ffmpeg(segments, str(podcast_path))
    if not ok:
        await state_manager.update_step_status(
            file_id, "compose_podcast", "failed", {"error": "concat_failed"}
        )
        raise RuntimeError("Podcast composition failed")

    # Upload to storage (prefer task-id naming)
    url = None
    try:
        sp = get_storage_provider()
        base_id = file_id
        # Prefer state.task_id
        if st and isinstance(st, dict) and st.get("task_id"):
            base_id = str(st["task_id"])  # prefer task-id naming
        else:
            # Try Redis mapping file->task
            try:
                task_id_hint = await state_manager.redis_client.get(
                    state_manager._get_file2task_key(file_id)
                )
                if task_id_hint:
                    base_id = str(task_id_hint)
            except Exception:
                pass
        object_key = f"{base_id}.mp3"
        url = sp.upload_file(str(podcast_path), object_key, "audio/mpeg")
    except Exception as e:
        logger.warning(f"Podcast upload failed: {e}")

    await state_manager.update_step_status(
        file_id,
        "compose_podcast",
        "completed",
        {"podcast_file": str(podcast_path), "storage_url": url},
    )
