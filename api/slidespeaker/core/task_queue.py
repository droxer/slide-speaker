"""
Task Queue System using Redis for distributed task processing.
This module provides the foundation for a master-worker architecture.
It handles task submission, status tracking, and distributed processing coordination.
"""

import json
import uuid
from typing import Any, cast

from loguru import logger

from slidespeaker.configs.db import db_enabled
from slidespeaker.repository.task import insert_task, update_task


def _filter_db_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Filter out sensitive information from kwargs before storing in database."""
    filtered = kwargs.copy()
    # Remove sensitive fields that shouldn't be persisted in database
    filtered.pop("file_path", None)
    return filtered


class RedisTaskQueue:
    """Redis-based task queue for distributed processing of presentation tasks"""

    def __init__(self) -> None:
        """Initialize the task queue with Redis client and key prefixes"""
        from slidespeaker.configs.redis_config import RedisConfig

        self.redis_client = RedisConfig.get_redis_client()
        self.task_prefix = "ss:task"
        self.queue_key = "ss:task_queue"

    def _get_task_key(self, task_id: str) -> str:
        """Generate Redis key for a task"""
        return f"{self.task_prefix}:{task_id}"

    async def submit_task(self, task_type: str, **kwargs: Any) -> str:
        """Submit a task to the Redis queue and return task ID"""
        task_id = str(uuid.uuid4())
        created_at = __import__("datetime").datetime.now().isoformat()

        task = {
            "task_id": task_id,
            "task_type": task_type,
            "status": "queued",
            "kwargs": kwargs,
            "result": None,
            "error": None,
            "created_at": created_at,
        }

        # Store task in Redis
        task_key = self._get_task_key(task_id)
        task_json = json.dumps(task)
        result = await self.redis_client.set(task_key, task_json)
        logger.info(f"Task {task_id} stored in Redis with result: {result}")

        # Persist in Postgres (optional)
        if db_enabled:
            try:
                # Filter out sensitive information before storing in database
                db_task = task.copy()
                db_task["kwargs"] = _filter_db_kwargs(task.get("kwargs", {}))
                await insert_task(db_task)
            except Exception as e:
                logger.warning(f"Failed to persist task {task_id} in DB: {e}")

        # Add task ID to queue - use RPUSH to maintain FIFO order
        queue_result = await self.redis_client.rpush(self.queue_key, task_id)  # type: ignore
        logger.info(
            f"Task ID {task_id} added to queue {self.queue_key} with RPUSH, result: {queue_result}"
        )

        # Log task summary
        file_id = kwargs.get("file_id", "unknown")
        logger.info(f"New task {task_id} created for file {file_id} at {created_at}")

        # Verify task was stored and queued
        stored_task = await self.redis_client.get(task_key)
        queue_length = await self.redis_client.llen(self.queue_key)  # type: ignore
        logger.debug(
            f"Task verification - task stored: {stored_task is not None}, queue length: {queue_length}"
        )

        if not stored_task:
            logger.warning(f"Failed to verify task storage for {task_key}")

        return task_id

    async def get_task(self, task_id: str) -> dict[str, Any] | None:
        """Get task details by ID from Redis storage"""
        task_key = self._get_task_key(task_id)
        task_data = await self.redis_client.get(task_key)

        if task_data:
            # Handle both bytes (from Redis) and string data
            if isinstance(task_data, bytes):
                task_data = task_data.decode("utf-8")
            try:
                return cast(dict[str, Any], json.loads(task_data))
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for task {task_id}: {e}")
                return None

        return None

    async def update_task_status(
        self, task_id: str, status: str, **kwargs: Any
    ) -> bool:
        """Update task status and additional fields in Redis"""
        task = await self.get_task(task_id)
        if not task:
            return False

        task["status"] = status
        task["updated_at"] = __import__("datetime").datetime.now().isoformat()

        # Update any additional fields
        for key, value in kwargs.items():
            task[key] = value

        task_key = self._get_task_key(task_id)
        await self.redis_client.set(task_key, json.dumps(task))
        logger.info(f"Task {task_id} status updated to {status}")
        # Mirror to DB
        if db_enabled:
            try:
                await update_task(task_id, status=status, error=task.get("error"))
            except Exception as e:
                logger.warning(f"Failed to update task {task_id} in DB: {e}")
        return True

    async def get_next_task(self) -> str | None:
        """Get the next task ID from the queue (non-blocking)"""
        task_id: str | None = None

        try:
            # Use rpop to get the task ID without moving it (safer approach)
            task_id_raw = await self.redis_client.brpop(self.queue_key, timeout=1)  # type: ignore
            if task_id_raw:
                task_id = str(task_id_raw[1])  # brpop returns tuple (key, value)
            else:
                pass  # No tasks in queue
        except Exception as e:
            logger.error(f"Error getting next task: {e}")

        return task_id

    async def complete_task_processing(self, task_id: str) -> bool:
        """Mark task as complete - no processing queue cleanup needed"""
        logger.info(f"Completing task processing for: {task_id}")
        return True

    async def get_task_status(self, task_id: str) -> str | None:
        """Get the status of a task from Redis storage"""
        task = await self.get_task(task_id)
        if task:
            return task.get("status")
        return None

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task if it's still queued or processing"""
        task = await self.get_task(task_id)
        if not task:
            logger.warning(f"Attempted to cancel non-existent task {task_id}")
            return False

        current_status = task["status"]
        if current_status == "queued":
            # Remove from queue - ignore return value
            removed_count = await self.redis_client.lrem(self.queue_key, 1, task_id)  # type: ignore
            task["status"] = "cancelled"
            task["error"] = "Task was cancelled by user"
            task_key = self._get_task_key(task_id)
            await self.redis_client.set(task_key, json.dumps(task))
            logger.info(
                f"Task {task_id} cancelled while queued (removed {removed_count} instances from queue)"
            )
            return True
        elif current_status == "processing":
            # For processing tasks, we mark as cancelled
            # The actual processing function would need to check for cancellation
            task["status"] = "cancelled"
            logger.info(
                f"Task {task_id} marked for cancellation (currently processing)"
            )
            task["error"] = "Task was cancelled by user"
            task_key = self._get_task_key(task_id)
            await self.redis_client.set(task_key, json.dumps(task))

            # Also store cancellation status in a separate key for immediate access
            cancellation_key = f"{self.task_prefix}:{task_id}:cancelled"
            await self.redis_client.setex(
                cancellation_key, 300, "true"
            )  # Expire after 5 minutes
            logger.info(f"Task {task_id} marked as cancelled during processing")
            return True
        else:
            # Task is already completed or failed
            return False

    async def is_task_cancelled(self, task_id: str) -> bool:
        """Check if a task has been cancelled by user"""
        # Check the main task status
        task = await self.get_task(task_id)
        if task and task.get("status") == "cancelled":
            return True

        # Also check for immediate cancellation flag
        cancellation_key = f"{self.task_prefix}:{task_id}:cancelled"
        exists_result = await self.redis_client.exists(cancellation_key)
        # Handle both int and bool returns from different Redis clients
        if isinstance(exists_result, bool):
            return exists_result
        return bool(exists_result > 0)


# Global task queue instance
task_queue = RedisTaskQueue()
