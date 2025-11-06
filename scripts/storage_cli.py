#!/usr/bin/env python3
"""Command line utilities for SlideSpeaker storage management."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

sys.path.append(".")

from rich.text import Text

from scripts._console_utils import get_console, status_label
from slidespeaker.configs.config import config, get_storage_provider
from slidespeaker.core.state_manager import state_manager
from slidespeaker.jobs.file_purger import FilePurger
from slidespeaker.storage.paths import OUTPUTS_PREFIX

SENSITIVE_TOKENS = ("secret", "password", "token", "key")

console = get_console()


def _redact_config(values: dict[str, Any]) -> dict[str, Any]:
    """Mask sensitive fields before printing configuration."""
    redacted: dict[str, Any] = {}
    for key, value in values.items():
        lowered = key.lower()
        if isinstance(value, str) and any(
            token in lowered for token in SENSITIVE_TOKENS
        ):
            redacted[key] = "*****"
        else:
            redacted[key] = value
    return redacted


def cmd_info(_: argparse.Namespace) -> None:
    provider_name = getattr(config, "storage_provider", "unknown")
    provider_cfg = getattr(config, "storage_config", {})
    console.print(f"[bold cyan]Active provider:[/] {provider_name}")
    if provider_cfg:
        console.print_json(data=_redact_config(provider_cfg), sort_keys=True)
    else:
        console.print("[dim]No storage configuration defined.[/]")


async def _gather_task_artifacts(task_id: str) -> tuple[str, list[str]]:
    """Collect storage keys for a task."""
    state = await state_manager.get_state_by_task(task_id)
    file_id: str | None = None
    file_ext: str | None = None
    if state:
        candidate = state.get("file_id")
        if isinstance(candidate, str) and candidate.strip():
            file_id = candidate.strip()
        state_ext = state.get("file_ext")
        if isinstance(state_ext, str) and state_ext.strip():
            file_ext = state_ext.strip()
    if not file_id:
        file_id = await state_manager.get_file_id_by_task(task_id)
    if not file_id:
        raise LookupError(f"Task '{task_id}' not found.")

    purger = FilePurger()
    storage_keys, _ = await purger.collect_artifacts(
        file_id,
        task_id=task_id,
        file_ext=file_ext,
    )

    if not storage_keys:
        return file_id, []

    outputs_prefix = f"{OUTPUTS_PREFIX}/"
    outputs_only = sorted(key for key in storage_keys if key.startswith(outputs_prefix))
    if outputs_only:
        return file_id, outputs_only
    return file_id, sorted(storage_keys)


def cmd_exists(args: argparse.Namespace) -> None:
    try:
        file_id, storage_keys = asyncio.run(_gather_task_artifacts(args.task_id))
    except LookupError as exc:
        console.print(f"[bold red]{exc}[/]")
        sys.exit(1)

    provider = get_storage_provider()
    results: list[tuple[str, bool]] = []
    for key in storage_keys:
        exists = False
        try:
            exists = provider.file_exists(key)
        except Exception as exc:  # noqa: BLE001
            console.print(f"[bold yellow]Error checking '{key}':[/] {exc}")
        results.append((key, exists))

    missing = [key for key, present in results if not present]

    if args.json:
        output = {
            "task_id": args.task_id,
            "file_id": file_id,
            "artifacts": [{"key": key, "exists": present} for key, present in results],
            "missing": missing,
        }
        console.print_json(data=output, sort_keys=True)
    else:
        header = Text.assemble(
            Text("Task ", style="bold cyan"),
            Text(args.task_id, style="bold white"),
            Text(" (file_id=", style="bold cyan"),
            Text(file_id, style="bold white"),
            Text(")", style="bold cyan"),
        )
        console.print(header)
        if not results:
            console.print("[bold yellow]No storage artifacts discovered.[/]")
        for key, present in results:
            status = status_label(
                "FOUND" if present else "MISSING",
                "bold green" if present else "bold red",
            )
            line = Text.assemble(status, Text(" "), Text(key, style="white"))
            console.print(line)
        if missing:
            console.print(
                f"[bold red]{len(missing)} artifact(s) missing.[/]",
            )

    if not results or missing:
        sys.exit(1)


def cmd_delete(args: argparse.Namespace) -> None:
    provider = get_storage_provider()
    if not args.force and not provider.file_exists(args.object_key):
        console.print(
            f"[bold red]Object '{args.object_key}' not found. Use --force to ignore.[/]"
        )
        sys.exit(1)

    try:
        provider.delete_file(args.object_key)
    except FileNotFoundError:
        if args.force:
            console.print(
                f"[bold yellow]Object '{args.object_key}' already absent (ignored).[/]"
            )
            return
        console.print(f"[bold red]Object '{args.object_key}' not found.[/]")
        sys.exit(1)

    console.print(f"[bold green]Object '{args.object_key}' deleted.[/]")


def cmd_download(args: argparse.Namespace) -> None:
    provider = get_storage_provider()
    destination = Path(args.destination).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        provider.download_file(args.object_key, str(destination))
    except FileNotFoundError:
        console.print(f"[bold red]Object '{args.object_key}' not found.[/]")
        sys.exit(1)
    console.print(
        f"[bold green]Downloaded[/] [white]{args.object_key}[/] "
        f"[bold green]to[/] [white]{destination}[/]"
    )


def cmd_upload(args: argparse.Namespace) -> None:
    provider = get_storage_provider()
    source = Path(args.file_path).expanduser()
    if not source.is_file():
        console.print(
            f"[bold red]Source file '{source}' does not exist or is not a file.[/]"
        )
        sys.exit(1)
    location = provider.upload_file(
        str(source), args.object_key, content_type=args.content_type
    )
    console.print(
        f"[bold green]Uploaded[/] [white]{source}[/] "
        f"[bold green]as[/] [white]{args.object_key}[/]"
    )
    if location:
        console.print(f"[bold cyan]Storage location:[/] {location}")


def cmd_url(args: argparse.Namespace) -> None:
    provider = get_storage_provider()
    url = provider.get_file_url(
        args.object_key,
        expires_in=args.expires,
        content_disposition=args.disposition,
        content_type=args.content_type,
    )
    console.print(Text(url, style="bold blue"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SlideSpeaker storage management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/storage_cli.py info
  python scripts/storage_cli.py exists <task_id>
  python scripts/storage_cli.py upload ./local.pdf ss:uploads/file.pdf
  python scripts/storage_cli.py download ss:uploads/file.pdf ./downloads/file.pdf
  python scripts/storage_cli.py url ss:uploads/file.pdf --expires 600
        """,
    )
    sub = parser.add_subparsers(dest="command")

    info_parser = sub.add_parser(
        "info", help="Show active storage provider configuration"
    )
    info_parser.set_defaults(func=cmd_info)

    exists_parser = sub.add_parser(
        "exists", help="Check generated artifacts for a task"
    )
    exists_parser.add_argument("task_id", help="Task identifier to inspect")
    exists_parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of human-readable text",
    )
    exists_parser.set_defaults(func=cmd_exists)

    delete_parser = sub.add_parser("delete", help="Delete an object from storage")
    delete_parser.add_argument("object_key", help="Object key to delete")
    delete_parser.add_argument(
        "--force",
        action="store_true",
        help="Do not error if the object is missing",
    )
    delete_parser.set_defaults(func=cmd_delete)

    download_parser = sub.add_parser(
        "download", help="Download an object to a local path"
    )
    download_parser.add_argument("object_key", help="Object key to download")
    download_parser.add_argument(
        "destination", help="Local path to store the downloaded file"
    )
    download_parser.set_defaults(func=cmd_download)

    upload_parser = sub.add_parser("upload", help="Upload a local file to storage")
    upload_parser.add_argument("file_path", help="Local file path to upload")
    upload_parser.add_argument("object_key", help="Object key destination in storage")
    upload_parser.add_argument(
        "--content-type",
        help="Optional MIME content type",
    )
    upload_parser.set_defaults(func=cmd_upload)

    url_parser = sub.add_parser("url", help="Generate a presigned URL for an object")
    url_parser.add_argument("object_key", help="Object key to generate URL for")
    url_parser.add_argument(
        "--expires",
        type=int,
        default=3600,
        help="Expiry in seconds (default: 3600)",
    )
    url_parser.add_argument(
        "--disposition",
        help="Optional content disposition value",
    )
    url_parser.add_argument(
        "--content-type",
        help="Optional response content type override",
    )
    url_parser.set_defaults(func=cmd_url)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not getattr(args, "command", None):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
