"""
Backfill storage object names to task-id-based keys.

Scans tasks from the database and ensures media/subtitle objects exist under
task-id-centric filenames:
- Audio (video narration and podcast): {task_id}.mp3
- Legacy podcast names also considered as sources: {file_id}_podcast.mp3
- Subtitles: {task_id}_{locale}.vtt|.srt

Usage examples:
  uv run python -m scripts.storage_backfill --dry-run
  uv run python -m scripts.storage_backfill --limit 200 --only subtitles
  uv run python -m scripts.storage_backfill --task-id <uuid> --force
"""

from __future__ import annotations

import argparse
import asyncio
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from loguru import logger

from slidespeaker.configs.config import get_storage_provider
from slidespeaker.configs.locales import locale_utils
from slidespeaker.core.state_manager import state_manager
from slidespeaker.repository.task import list_tasks


def _iter_locales_from_state(state: dict[str, Any]) -> Iterable[str]:
    seen: set[str] = set()
    lang = state.get("subtitle_language") or state.get("voice_language")
    if isinstance(lang, str) and lang:
        seen.add(locale_utils.get_locale_code(lang))
    steps = state.get("steps") or {}
    for key in ("generate_subtitles", "generate_pdf_subtitles"):
        data = (steps.get(key) or {}).get("data") or {}
        files = data.get("subtitle_files") or []
        for p in files:
            if not isinstance(p, str):
                continue
            m = re.search(r"_([A-Za-z-]+)\.(vtt|srt)$", p)
            if m:
                seen.add(m.group(1))
    return sorted(seen)


@dataclass
class Stats:
    scanned_tasks: int = 0
    audio_copied: int = 0
    podcast_copied: int = 0
    subtitles_copied: int = 0
    skipped_existing: int = 0
    errors: int = 0
    audio_legacy_deleted: int = 0
    podcast_legacy_deleted: int = 0
    subtitles_legacy_deleted: int = 0


async def backfill_task(
    task: dict[str, Any],
    *,
    only: str,
    dry_run: bool,
    force: bool,
    delete_legacy: bool,
    stats: Stats,
) -> None:
    sp = get_storage_provider()
    task_id = task["task_id"]
    file_id = task["file_id"]
    # task_type available if needed in future
    _tt = (task.get("task_type") or "").lower()

    stats.scanned_tasks += 1

    # 1) Audio (video narration): ensure {task_id}.mp3 exists if a file-id-based audio exists
    if only in ("all", "audio", "video"):
        src_keys = [
            f"{file_id}.mp3",
            f"{file_id}_final_audio.mp3",
            f"{file_id}_final.mp3",
        ]
        dst_key = f"{task_id}.mp3"
        src = next((k for k in src_keys if sp.file_exists(k)), None)
        if src:
            if sp.file_exists(dst_key) and not force:
                stats.skipped_existing += 1
            else:
                logger.info(f"Backfill audio: {src} -> {dst_key} (task {task_id})")
                if not dry_run:
                    try:
                        blob = sp.download_bytes(src)
                        sp.upload_bytes(blob, dst_key, content_type="audio/mpeg")
                        stats.audio_copied += 1
                        if delete_legacy and src != dst_key:
                            try:
                                sp.delete_file(src)
                                stats.audio_legacy_deleted += 1
                            except Exception as e:
                                stats.errors += 1
                                logger.error(
                                    f"Audio legacy delete error for {task_id}: {e}"
                                )
                    except Exception as e:
                        stats.errors += 1
                        logger.error(f"Audio backfill error for {task_id}: {e}")

    # 2) Podcast: ensure {task_id}.mp3 exists if any podcast-named source exists
    if only in ("all", "audio", "podcast"):
        src_keys = [
            f"{file_id}.mp3",
            f"{task_id}_podcast.mp3",
            f"{file_id}_podcast.mp3",
        ]
        dst_key = f"{task_id}.mp3"
        src = next((k for k in src_keys if sp.file_exists(k)), None)
        if src:
            if sp.file_exists(dst_key) and not force:
                stats.skipped_existing += 1
            else:
                logger.info(f"Backfill podcast: {src} -> {dst_key} (task {task_id})")
                if not dry_run:
                    try:
                        blob = sp.download_bytes(src)
                        sp.upload_bytes(blob, dst_key, content_type="audio/mpeg")
                        stats.podcast_copied += 1
                        if delete_legacy and src != dst_key:
                            try:
                                sp.delete_file(src)
                                stats.podcast_legacy_deleted += 1
                            except Exception as e:
                                stats.errors += 1
                                logger.error(
                                    f"Podcast legacy delete error for {task_id}: {e}"
                                )
                    except Exception as e:
                        stats.errors += 1
                        logger.error(f"Podcast backfill error for {task_id}: {e}")

    # 3) Subtitles: ensure {task_id}_{loc}.vtt|.srt exist
    if only in ("all", "subtitles"):
        st = await state_manager.get_state(file_id)
        locales = list(_iter_locales_from_state(st or {}))
        for loc in locales:
            for ext, ctype in (("vtt", "text/vtt"), ("srt", "text/plain")):
                dst_key = f"{task_id}_{loc}.{ext}"
                if not force and sp.file_exists(dst_key):
                    continue
                # Prefer copying from cloud key if present
                src_key = None
                for cand in (
                    f"{file_id}_{loc}.{ext}",
                    f"{file_id}_final_{loc}.{ext}",
                    f"{file_id}_final.{ext}",
                ):
                    if sp.file_exists(cand):
                        src_key = cand
                        break
                if src_key:
                    if sp.file_exists(dst_key) and not force:
                        stats.skipped_existing += 1
                        continue
                    logger.info(
                        f"Backfill subtitles: {src_key} -> {dst_key} (task {task_id})"
                    )
                    if not dry_run:
                        try:
                            blob = sp.download_bytes(src_key)
                            sp.upload_bytes(blob, dst_key, content_type=ctype)
                            stats.subtitles_copied += 1
                            if delete_legacy and src_key != dst_key:
                                try:
                                    sp.delete_file(src_key)
                                    stats.subtitles_legacy_deleted += 1
                                except Exception as e:
                                    stats.errors += 1
                                    logger.error(
                                        f"Subtitle legacy delete error for {task_id} [{loc}.{ext}]: {e}"
                                    )
                        except Exception as e:
                            stats.errors += 1
                            logger.error(
                                f"Subtitle backfill error for {task_id} [{loc}.{ext}]: {e}"
                            )


async def main() -> None:
    ap = argparse.ArgumentParser(
        description="Backfill storage object names to task-id-based keys"
    )
    ap.add_argument(
        "--dry-run", action="store_true", help="Do not write, only log actions"
    )
    ap.add_argument("--limit", type=int, default=200, help="Batch size per DB page")
    ap.add_argument("--offset", type=int, default=0, help="Starting offset")
    ap.add_argument(
        "--only",
        choices=["all", "audio", "podcast", "video", "subtitles"],
        default="all",
        help="Which assets to backfill",
    )
    ap.add_argument("--task-id", type=str, default=None, help="Backfill a single task")
    ap.add_argument(
        "--force", action="store_true", help="Overwrite destination keys if present"
    )
    ap.add_argument(
        "--delete-legacy",
        action="store_true",
        help="Delete legacy file-id-based keys after successful copy to task-id naming",
    )
    args = ap.parse_args()

    if args.task_id:
        # Fast path: fetch single task directly from DB
        from slidespeaker.repository.task import get_task as db_get_task

        stats = Stats()
        found = await db_get_task(args.task_id)
        if not found:
            logger.error(f"Task {args.task_id} not found")
            return
        await backfill_task(
            found,
            only=args.only,
            dry_run=args.dry_run,
            force=args.force,
            delete_legacy=args.delete_legacy,
            stats=stats,
        )
        logger.info(
            (
                "Summary: scanned={} audio_copied={} podcast_copied={} "
                "subtitles_copied={} skipped={} errors={} "
                "audio_legacy_deleted={} podcast_legacy_deleted={} "
                "subtitles_legacy_deleted={}"
            ),
            stats.scanned_tasks,
            stats.audio_copied,
            stats.podcast_copied,
            stats.subtitles_copied,
            stats.skipped_existing,
            stats.errors,
            stats.audio_legacy_deleted,
            stats.podcast_legacy_deleted,
            stats.subtitles_legacy_deleted,
        )
        return

    # Iterate pages
    offset = args.offset
    total = None
    stats = Stats()
    while True:
        page = await list_tasks(limit=args.limit, offset=offset, status=None)
        tasks = page.get("tasks", [])
        total = page.get("total", total)
        if not tasks:
            break
        for t in tasks:
            await backfill_task(
                t,
                only=args.only,
                dry_run=args.dry_run,
                force=args.force,
                delete_legacy=args.delete_legacy,
                stats=stats,
            )
        offset += len(tasks)
        if total is not None and offset >= int(total):
            break

    logger.info(
        (
            "Summary: scanned={} audio_copied={} podcast_copied={} "
            "subtitles_copied={} skipped={} errors={} "
            "audio_legacy_deleted={} podcast_legacy_deleted={} "
            "subtitles_legacy_deleted={}"
        ),
        stats.scanned_tasks,
        stats.audio_copied,
        stats.podcast_copied,
        stats.subtitles_copied,
        stats.skipped_existing,
        stats.errors,
        stats.audio_legacy_deleted,
        stats.podcast_legacy_deleted,
        stats.subtitles_legacy_deleted,
    )


if __name__ == "__main__":
    asyncio.run(main())
