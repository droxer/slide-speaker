#!/usr/bin/env python3
"""Command line utilities for managing SlideSpeaker users."""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any

sys.path.append(".")

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from scripts._console_utils import get_console, status_label
from slidespeaker.repository import user as user_repo

console = get_console()


def _print_user(user: dict[str, Any]) -> None:
    created = user.get("created_at") or "?"
    updated = user.get("updated_at") or "?"
    language = user.get("preferred_language") or "english"
    text = Text()
    text.append("id=", style="dim")
    text.append(str(user.get("id")), style="bold white")
    text.append(" email=", style="dim")
    text.append(str(user.get("email")), style="bold cyan")
    text.append(" name=", style="dim")
    text.append(str(user.get("name") or "-"), style="white")
    text.append(" language=", style="dim")
    text.append(str(language), style="bold green")
    text.append(" created=", style="dim")
    text.append(str(created), style="white")
    text.append(" updated=", style="dim")
    text.append(str(updated), style="white")
    console.print(text)


async def cmd_list(args: argparse.Namespace) -> None:
    users = await user_repo.list_users(limit=args.limit, offset=args.offset)
    if args.json:
        console.print_json(data=users)
        return
    if not users:
        console.print("[bold yellow]No users found.[/]")
        return
    table = Table(
        title=f"{len(users)} user(s)",
        header_style="bold cyan",
        show_lines=False,
    )
    table.add_column("ID", style="bold white")
    table.add_column("Email", style="bold cyan")
    table.add_column("Name")
    table.add_column("Language", style="bold green")
    table.add_column("Created")
    table.add_column("Updated")
    for user in users:
        table.add_row(
            str(user.get("id")),
            str(user.get("email")),
            str(user.get("name") or "-"),
            str(user.get("preferred_language") or "english"),
            str(user.get("created_at") or "?"),
            str(user.get("updated_at") or "?"),
        )
    console.print(table)


async def cmd_show(args: argparse.Namespace) -> None:
    user: dict[str, Any] | None = None
    if args.email:
        user = await user_repo.get_user_by_email(args.email)
    elif args.user_id:
        user = await user_repo.get_user_by_id(args.user_id)
    if not user:
        console.print("[bold red]User not found.[/]")
        sys.exit(1)
    if args.json:
        console.print_json(data=user)
    else:
        panel_text = Text()
        for key, value in sorted(user.items()):
            panel_text.append(f"{key}: ", style="bold cyan")
            panel_text.append(f"{value}\n", style="white")
        console.print(Panel.fit(panel_text, title="User Details", border_style="cyan"))


async def cmd_create(args: argparse.Namespace) -> None:
    try:
        user = await user_repo.create_user_with_password(
            email=args.email,
            password=args.password,
            name=args.name,
            preferred_language=args.preferred_language,
        )
    except ValueError as exc:
        console.print(f"[bold red]Failed to create user:[/] {exc}")
        sys.exit(1)
    console.print(status_label("CREATED", "bold green"))
    _print_user(user)


async def cmd_set_password(args: argparse.Namespace) -> None:
    target = await user_repo.get_user_by_email(args.email)
    if not target:
        console.print("[bold red]User not found.[/]")
        sys.exit(1)
    updated = await user_repo.set_user_password(target["id"], args.password)
    if not updated:
        console.print("[bold red]Password update failed.[/]")
        sys.exit(1)
    console.print("[bold green]Password updated successfully.[/]")


async def cmd_delete(args: argparse.Namespace) -> None:
    user = await user_repo.get_user_by_email(args.email)
    if not user:
        console.print("[bold red]User not found.[/]")
        sys.exit(1)
    removed = await user_repo.delete_user(user["id"])
    if not removed:
        console.print("[bold red]Delete operation failed.[/]")
        sys.exit(1)
    console.print("[bold green]User deleted.[/]")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="SlideSpeaker user management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python api/scripts/user_cli.py list
  python api/scripts/user_cli.py create --email foo@example.com --password secret --name "Foo"
  python api/scripts/user_cli.py show --email foo@example.com
  python api/scripts/user_cli.py set-password --email foo@example.com --password newpass
  python api/scripts/user_cli.py delete --email foo@example.com
        """,
    )

    sub = parser.add_subparsers(dest="command")

    list_parser = sub.add_parser("list", help="List users")
    list_parser.add_argument(
        "--limit", type=int, default=50, help="Maximum results (default: 50)"
    )
    list_parser.add_argument(
        "--offset", type=int, default=0, help="Results offset (default: 0)"
    )
    list_parser.add_argument("--json", action="store_true", help="Output JSON")

    show_parser = sub.add_parser("show", help="Show a single user")
    show_group = show_parser.add_mutually_exclusive_group(required=True)
    show_group.add_argument("--email", help="User email")
    show_group.add_argument("--user-id", help="User id")
    show_parser.add_argument("--json", action="store_true", help="Output JSON")

    create_parser = sub.add_parser("create", help="Create a new user")
    create_parser.add_argument("--email", required=True, help="Email for the user")
    create_parser.add_argument("--password", required=True, help="Initial password")
    create_parser.add_argument("--name", help="Optional display name")
    create_parser.add_argument(
        "--preferred-language",
        default="english",
        help="Preferred language code (default: english)",
    )

    pw_parser = sub.add_parser("set-password", help="Set password for a user")
    pw_parser.add_argument("--email", required=True, help="User email")
    pw_parser.add_argument("--password", required=True, help="New password value")

    delete_parser = sub.add_parser("delete", help="Delete a user by email")
    delete_parser.add_argument("--email", required=True, help="User email")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    if args.command == "list":
        await cmd_list(args)
    elif args.command == "show":
        await cmd_show(args)
    elif args.command == "create":
        await cmd_create(args)
    elif args.command == "set-password":
        await cmd_set_password(args)
    elif args.command == "delete":
        await cmd_delete(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
