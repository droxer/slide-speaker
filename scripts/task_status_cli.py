#!/usr/bin/env python3
"""Command line utilities for inspecting and updating Redis task statuses."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

sys.path.append(".")

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from scripts._console_utils import get_console, status_label
from slidespeaker.core.state_manager import state_manager
from slidespeaker.core.task_queue import task_queue

VALID_STATUSES = {"queued", "processing", "completed", "failed", "cancelled"}
STATUS_STYLES = {
    "queued": "yellow",
    "processing": "bold cyan",
    "completed": "bold green",
    "failed": "bold red",
    "cancelled": "bold magenta",
}

console = get_console()


async def _load_task(key: str) -> dict[str, Any] | None:
    """Fetch and decode a task document stored in Redis."""
    raw = await task_queue.redis_client.get(key)
    if not raw:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    try:
        task = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if "task_id" not in task:
        task["task_id"] = key.split(":", maxsplit=2)[-1]
    return task


def _sort_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort task records by created_at descending."""
    return sorted(
        tasks,
        key=lambda item: item.get("created_at") or "",
        reverse=True,
    )


async def fetch_tasks(
    *, status: str | None = None, limit: int | None = 50
) -> list[dict[str, Any]]:
    """Retrieve tasks from Redis with optional status filtering."""
    tasks: list[dict[str, Any]] = []
    cursor: int = 0
    while True:
        cursor, keys = await task_queue.redis_client.scan(
            cursor=cursor, match="ss:task:*", count=500
        )
        for key in keys:
            key_str = key.decode("utf-8") if isinstance(key, bytes) else str(key)
            task = await _load_task(key_str)
            if not task:
                continue
            if status and task.get("status") != status:
                continue
            tasks.append(task)
            if limit is not None and len(tasks) >= limit:
                return _sort_tasks(tasks)
        if cursor == 0:
            break
    return _sort_tasks(tasks)


async def set_task_status(
    task_id: str, status: str, *, error: str | None = None, clear_error: bool = False
) -> bool:
    """Update task status in Redis (and mirrored state) for a task."""
    normalized = status.lower()
    if normalized not in VALID_STATUSES:
        raise ValueError(f"Unsupported status '{status}'.")
    if error and clear_error:
        raise ValueError("Cannot use --error and --clear-error together.")

    update_kwargs: dict[str, Any] = {}
    if clear_error:
        update_kwargs["error"] = None
    elif error is not None:
        update_kwargs["error"] = error

    updated = await task_queue.update_task_status(task_id, normalized, **update_kwargs)
    if not updated:
        return False

    if normalized == "completed":
        await state_manager.mark_completed_by_task(task_id)
    elif normalized == "failed":
        await state_manager.mark_failed_by_task(task_id)
    elif normalized == "cancelled":
        await state_manager.mark_cancelled_by_task(task_id)
    else:
        await state_manager.set_status_by_task(task_id, normalized)

    return True


def _print_task(task: dict[str, Any]) -> None:
    """Pretty-print a task record."""
    task_id = task.get("task_id") or task.get("id") or "-"
    status = task.get("status") or "-"
    created = task.get("created_at") or "-"
    updated = task.get("updated_at") or "-"
    user_id = task.get("user_id") or "-"
    error = task.get("error")
    source = task.get("kwargs", {}).get("file_id", "-")
    text = Text()
    text.append(task_id, style="bold white")
    text.append(" status=", style="dim")
    text.append(status, style=STATUS_STYLES.get(status, "white"))
    text.append(" created=", style="dim")
    text.append(created, style="white")
    text.append(" updated=", style="dim")
    text.append(updated, style="white")
    text.append(" user=", style="dim")
    text.append(user_id, style="white")
    text.append(" file=", style="dim")
    text.append(str(source), style="white")
    if error:
        text.append(" error=", style="dim")
        text.append(str(error), style="bold red")
    console.print(text)


async def cmd_list(args: argparse.Namespace) -> None:
    status = args.status.lower() if args.status else None
    tasks = await fetch_tasks(
        status=status,
        limit=None if args.all else args.limit,
    )
    if args.json:
        console.print_json(data=tasks)
        return
    if not tasks:
        console.print("[bold yellow]No tasks found.[/]")
        return
    table = Table(
        title=f"{len(tasks)} task(s) found",
        header_style="bold cyan",
        show_lines=False,
    )
    table.add_column("Task ID", style="bold white")
    table.add_column("Status")
    table.add_column("Created")
    table.add_column("Updated")
    table.add_column("User")
    table.add_column("File")
    table.add_column("Error", style="bold red")
    for task in tasks:
        status_value = task.get("status") or "-"
        table.add_row(
            str(task.get("task_id") or task.get("id") or "-"),
            Text(str(status_value), style=STATUS_STYLES.get(status_value, "white")),
            str(task.get("created_at") or "-"),
            str(task.get("updated_at") or "-"),
            str(task.get("user_id") or "-"),
            str(task.get("kwargs", {}).get("file_id", "-")),
            str(task.get("error") or ""),
        )
    console.print(table)


async def cmd_show(args: argparse.Namespace) -> None:
    task = await task_queue.get_task(args.task_id)
    if not task:
        console.print(f"[bold red]Task {args.task_id} not found.[/]")
        sys.exit(1)
    if args.json:
        console.print_json(data=task)
    else:
        content = Text()
        for key, value in sorted(task.items()):
            display = (
                json.dumps(value, default=str)
                if isinstance(value, dict | list)
                else value
            )
            content.append(f"{key}: ", style="bold cyan")
            content.append(f"{display}\n", style="white")
        console.print(
            Panel.fit(content, title=f"Task {args.task_id}", border_style="cyan")
        )


async def cmd_set_status(args: argparse.Namespace) -> None:
    try:
        success = await set_task_status(
            args.task_id,
            args.status,
            error=args.error,
            clear_error=args.clear_error,
        )
    except ValueError as exc:
        console.print(f"[bold red]{exc}[/]")
        sys.exit(1)

    if not success:
        console.print(f"[bold red]Task {args.task_id} not found.[/]")
        sys.exit(1)
    label = status_label("OK", "bold green")
    message = Text.assemble(
        label,
        Text(" Task ", style="bold white"),
        Text(args.task_id, style="bold cyan"),
        Text(" status updated to ", style="bold white"),
        Text(args.status, style=STATUS_STYLES.get(args.status, "white")),
    )
    console.print(message)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SlideSpeaker Redis task status manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/task_status_cli.py list
  python scripts/task_status_cli.py list --status failed --limit 10
  python scripts/task_status_cli.py show <task_id>
  python scripts/task_status_cli.py set-status <task_id> failed --error "Manual failure"
        """,
    )
    sub = parser.add_subparsers(dest="command")

    list_parser = sub.add_parser("list", help="List Redis tasks")
    list_parser.add_argument(
        "--status",
        choices=sorted(VALID_STATUSES),
        help="Filter tasks by status",
    )
    list_parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of tasks to display (default: 50)",
    )
    list_parser.add_argument(
        "--all",
        action="store_true",
        help="Display all tasks (overrides --limit)",
    )
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of human-readable text",
    )
    list_parser.set_defaults(func=cmd_list)

    show_parser = sub.add_parser("show", help="Show a single Redis task")
    show_parser.add_argument("task_id", help="Task identifier")
    show_parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of human-readable text",
    )
    show_parser.set_defaults(func=cmd_show)

    status_parser = sub.add_parser("set-status", help="Update the status of a task")
    status_parser.add_argument("task_id", help="Task identifier")
    status_parser.add_argument(
        "status",
        choices=sorted(VALID_STATUSES),
        help="New status value",
    )
    status_parser.add_argument(
        "--error",
        help="Optional error message to save with the task",
    )
    status_parser.add_argument(
        "--clear-error",
        action="store_true",
        help="Clear any stored error on the task",
    )
    status_parser.set_defaults(func=cmd_set_status)

    return parser


async def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not getattr(args, "command", None):
        parser.print_help()
        return
    await args.func(args)


if __name__ == "__main__":
    asyncio.run(main())
