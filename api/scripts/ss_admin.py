#!/usr/bin/env python3
"""
SlideSpeaker admin CLI

Maintenance utilities for Redis-backed state:
 - purge-legacy-file-states: remove file-id states when task-alias exists
 - set-type: set task_type and video/podcast flags for a specific task

Usage examples:
  uv run python -m api.scripts.ss_admin purge-legacy-file-states
  uv run python -m api.scripts.ss_admin \
    set-type --task-id <uuid> --task-type podcast \
    --no-generate-video --generate-podcast
"""

from __future__ import annotations

import argparse
import asyncio
from typing import Any

from dotenv import load_dotenv

# Ensure env is loaded (OPENAI/REDIS, etc.)
load_dotenv()

# Lazy imports after dotenv
from slidespeaker.core.state_manager import state_manager  # noqa: E402


async def purge_legacy_file_states() -> dict[str, Any]:
    removed = 0
    checked = 0
    errors: list[str] = []

    # Scan all file-id states
    try:
        # scan_iter returns an async generator in redis.asyncio
        async for key in state_manager.redis_client.scan_iter(match="ss:state:*"):
            try:
                k = str(key)
                if k.startswith("ss:state:task:"):
                    continue
                fid = k.replace("ss:state:", "")
                # If we have any task mapping for this file, remove the file-id state
                mapped = await state_manager.redis_client.get(f"ss:file2task:{fid}")
                has_set = await state_manager.redis_client.exists(
                    f"ss:file2tasks:{fid}"
                )
                checked += 1
                if mapped or has_set:
                    await state_manager.redis_client.delete(k)
                    removed += 1
            except Exception as e:  # noqa: BLE001
                errors.append(str(e))
                continue
    except Exception as e:  # noqa: BLE001
        errors.append(str(e))

    return {"checked": checked, "removed": removed, "errors": errors}


async def set_task_type(
    task_id: str,
    task_type: str | None,
    generate_video: bool | None,
    generate_podcast: bool | None,
) -> dict[str, Any]:
    st = await state_manager.get_state_by_task(task_id)
    if not st:
        return {"updated": False, "error": "state_not_found", "task_id": task_id}
    if task_type is not None:
        st["task_type"] = task_type
    if generate_video is not None:
        st["generate_video"] = generate_video
    if generate_podcast is not None:
        st["generate_podcast"] = generate_podcast
    st["task_id"] = task_id
    # Persist under task alias and remove legacy file-id mirror (state manager handles deletion)
    fid = st.get("file_id")
    if isinstance(fid, str) and fid:
        await state_manager.save_state(fid, st)
    else:
        await state_manager.redis_client.set(
            f"ss:state:task:{task_id}", __import__("json").dumps(st), ex=86400
        )
    return {"updated": True, "task_id": task_id}


def _bool_flag(parser: argparse.ArgumentParser, name: str, dest: str) -> None:
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument(f"--{name}", dest=dest, action="store_true")
    grp.add_argument(f"--no-{name}", dest=dest, action="store_false")
    parser.set_defaults(**{dest: None})  # keep None when not provided


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ss-admin", description="SlideSpeaker admin CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser(
        "purge-legacy-file-states",
        help="Remove ss:state:{file_id} keys when a task alias exists",
    )

    sp = sub.add_parser(
        "set-type",
        help="Set task_type and video/podcast flags for a task",
    )
    sp.add_argument("--task-id", required=True, help="Target task ID")
    sp.add_argument(
        "--task-type",
        choices=["video", "podcast", "both"],
        help="Explicit task type label",
    )
    _bool_flag(sp, "generate-video", "generate_video")
    _bool_flag(sp, "generate-podcast", "generate_podcast")

    return p


async def main_async(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "purge-legacy-file-states":
        res = await purge_legacy_file_states()
        print(res)
        return 0
    if args.cmd == "set-type":
        res = await set_task_type(
            task_id=args.task_id,
            task_type=args.task_type,
            generate_video=args.generate_video,
            generate_podcast=args.generate_podcast,
        )
        if not res.get("updated"):
            print(res)
            return 1
        print(res)
        return 0

    parser.print_help()
    return 2


def main() -> None:
    raise SystemExit(asyncio.run(main_async()))


if __name__ == "__main__":
    main()
