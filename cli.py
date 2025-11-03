#!/usr/bin/env python3
"""
CLI tool for managing SlideSpeaker tasks.

This tool provides command-line interface for:
- Listing tasks
- Cancelling tasks
- Deleting task state
- Viewing task details
- Migrating tasks from Redis to PostgreSQL
"""

import argparse
import asyncio
import json
import sys
from typing import Any

# Add the api directory to the path so we can import slidespeaker modules
sys.path.append(".")

from slidespeaker.core.state_manager import state_manager
from slidespeaker.core.task_queue import task_queue


async def list_tasks() -> None:
    """List all tasks in the system."""
    print("Listing tasks is not directly supported by the current implementation.")
    print("Tasks are stored in Redis with keys starting with 'ss:task:'")
    print("You can use Redis CLI to inspect tasks directly.")


async def get_task_details(task_id: str) -> dict[str, Any] | None:
    """Get detailed information about a specific task."""
    task = await task_queue.get_task(task_id)
    return task


async def cancel_task(task_id: str) -> bool:
    """Cancel a task by ID."""
    try:
        success = await task_queue.cancel_task(task_id)
        return success
    except Exception as e:
        print(f"Error cancelling task {task_id}: {e}")
        return False


async def delete_task_state(file_id: str) -> bool:
    """Delete task state from Redis."""
    try:
        # Delete the state
        state_key = f"ss:state:{file_id}"
        result = await state_manager.redis_client.delete(state_key)

        # Also delete the task if it exists
        task_key = f"ss:task:{file_id}"
        await state_manager.redis_client.delete(task_key)

        return bool(result > 0)
    except Exception as e:
        print(f"Error deleting task state for {file_id}: {e}")
        return False


async def list_all_task_states() -> None:
    """List all task states in the system."""
    try:
        # Scan for all state keys
        pattern = "ss:state:*"
        cursor = 0
        states = []

        while True:
            cursor, keys = await state_manager.redis_client.scan(cursor, match=pattern)
            states.extend(keys)
            if cursor == 0:
                break

        if not states:
            print("No task states found.")
            return

        print(f"Found {len(states)} task states:")
        for key in states:
            # Handle both bytes and string keys
            if isinstance(key, bytes):
                file_id = key.decode("utf-8").replace("ss:state:", "")
            else:
                file_id = str(key).replace("ss:state:", "")
            state = await state_manager.get_state(file_id)
            if state:
                status = state.get("status", "unknown")
                created_at = state.get("created_at", "unknown")
                print(f"  {file_id}: {status} (created: {created_at})")
    except Exception as e:
        print(f"Error listing task states: {e}")
        import traceback

        traceback.print_exc()


async def main() -> None:
    """Main entry point for the CLI tool."""
    parser = argparse.ArgumentParser(
        description="SlideSpeaker Task Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cli.py list-states                    # List all task states
  cli.py get-task <task_id>             # Get details of a specific task
  cli.py cancel-task <task_id>          # Cancel a task
  cli.py delete-state <file_id>         # Delete a task state
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List states command
    subparsers.add_parser("list-states", help="List all task states")

    # Get task command
    get_parser = subparsers.add_parser("get-task", help="Get task details")
    get_parser.add_argument("task_id", help="Task ID to retrieve")

    # Cancel task command
    cancel_parser = subparsers.add_parser("cancel-task", help="Cancel a task")
    cancel_parser.add_argument("task_id", help="Task ID to cancel")

    # Delete state command
    delete_parser = subparsers.add_parser("delete-state", help="Delete task state")
    delete_parser.add_argument("file_id", help="File ID to delete state for")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "list-states":
        await list_all_task_states()
    elif args.command == "get-task":
        task = await get_task_details(args.task_id)
        if task:
            print(json.dumps(task, indent=2))
        else:
            print(f"Task {args.task_id} not found")
            sys.exit(1)
    elif args.command == "cancel-task":
        success = await cancel_task(args.task_id)
        if success:
            print(f"Task {args.task_id} cancelled successfully")
        else:
            print(f"Failed to cancel task {args.task_id}")
            sys.exit(1)
    elif args.command == "delete-state":
        success = await delete_task_state(args.file_id)
        if success:
            print(f"Task state for {args.file_id} deleted successfully")
        else:
            print(f"Failed to delete task state for {args.file_id} or state not found")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
