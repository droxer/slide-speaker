#!/usr/bin/env python3
"""Command line utilities for managing SlideSpeaker users."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

sys.path.append(".")

from slidespeaker.repository import user as user_repo


def _print_user(user: dict[str, Any]) -> None:
    created = user.get("created_at") or "?"
    updated = user.get("updated_at") or "?"
    language = user.get("preferred_language") or "english"
    print(
        f"id={user.get('id')} email={user.get('email')} name={user.get('name') or '-'} "
        f"language={language} created={created} updated={updated}"
    )


async def cmd_list(args: argparse.Namespace) -> None:
    users = await user_repo.list_users(limit=args.limit, offset=args.offset)
    if args.json:
        print(json.dumps(users, indent=2))
        return
    if not users:
        print("No users found.")
        return
    for user in users:
        _print_user(user)


async def cmd_show(args: argparse.Namespace) -> None:
    user: dict[str, Any] | None = None
    if args.email:
        user = await user_repo.get_user_by_email(args.email)
    elif args.user_id:
        user = await user_repo.get_user_by_id(args.user_id)
    if not user:
        print("User not found.")
        sys.exit(1)
    if args.json:
        print(json.dumps(user, indent=2))
    else:
        _print_user(user)


async def cmd_create(args: argparse.Namespace) -> None:
    try:
        user = await user_repo.create_user_with_password(
            email=args.email,
            password=args.password,
            name=args.name,
            preferred_language=args.preferred_language,
        )
    except ValueError as exc:
        print(f"Failed to create user: {exc}")
        sys.exit(1)
    _print_user(user)


async def cmd_set_password(args: argparse.Namespace) -> None:
    target = await user_repo.get_user_by_email(args.email)
    if not target:
        print("User not found.")
        sys.exit(1)
    updated = await user_repo.set_user_password(target["id"], args.password)
    if not updated:
        print("Password update failed.")
        sys.exit(1)
    print("Password updated successfully.")


async def cmd_delete(args: argparse.Namespace) -> None:
    user = await user_repo.get_user_by_email(args.email)
    if not user:
        print("User not found.")
        sys.exit(1)
    removed = await user_repo.delete_user(user["id"])
    if not removed:
        print("Delete operation failed.")
        sys.exit(1)
    print("User deleted.")


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
