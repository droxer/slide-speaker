"""
Task Queue System using Redis for distributed task processing.
This module provides the foundation for a master-worker architecture.
"""

import json
import os
import uuid
from typing import Any, cast

import redis.asyncio as redis
from dotenv import load_dotenv
from loguru import logger

load_dotenv()


class RedisTaskQueue:
    """Redis-based task queue for distributed processing"""

    def __init__(self) -> None:
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0)),
            password=os.getenv("REDIS_PASSWORD", None),
            decode_responses=True,
            socket_timeout=5.0,
        )
        self.task_prefix = "ai_slider:task"
        self.queue_key = "ai_slider:task_queue"

    def _get_task_key(self, task_id: str) -> str:
        """Generate Redis key for a task"""
        return f"{self.task_prefix}:{task_id}"

    async def submit_task(self, task_type: str, **kwargs: Any) -> str:
        """Submit a task to the Redis queue and return task ID"""
        task_id = str(uuid.uuid4())
        task = {
            "task_id": task_id,
            "task_type": task_type,
            "status": "queued",
            "kwargs": kwargs,
            "result": None,
            "error": None,
            "created_at": __import__("datetime").datetime.now().isoformat(),
        }

        # Store task in Redis
        task_key = self._get_task_key(task_id)
        await self.redis_client.set(task_key, json.dumps(task))

        # Add task ID to queue
        await self.redis_client.lpush(self.queue_key, task_id)

        logger.info(f"Task {task_id} submitted to Redis queue: {task_type}")
        return task_id

    async def get_task(self, task_id: str) -> dict[str, Any] | None:
        """Get task details by ID"""
        task_key = self._get_task_key(task_id)
        task_data = await self.redis_client.get(task_key)
        if task_data:
            # Handle both bytes (from Redis) and string data
            if isinstance(task_data, bytes):
                task_data = task_data.decode('utf-8')
            return cast(dict[str, Any], json.loads(task_data))
        return None

    async def update_task_status(self, task_id: str, status: str, **kwargs: Any) -> bool:
        """Update task status and additional fields"""
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
        return True

    async def get_next_task(self) -> str | None:
        """Get the next task ID from the queue (non-blocking)"""
        task_id: str | None = None
        try:
            # Use blmove for Redis 6.2+ (replaces deprecated brpoplpush)
            task_id_raw = await self.redis_client.blmove(
                self.queue_key,
                f"{self.queue_key}:processing",
                1,  # timeout
                "RIGHT",
                "LEFT",
            )
            task_id = str(task_id_raw) if task_id_raw is not None else None
        except AttributeError:
            # Fallback to brpoplpush for older Redis versions
            task_id_raw = await self.redis_client.brpoplpush(  # type: ignore
                self.queue_key, f"{self.queue_key}:processing", timeout=1
            )
            task_id = str(task_id_raw) if task_id_raw is not None else None

        return task_id

    async def complete_task_processing(self, task_id: str) -> bool:
        """Move task from processing queue back to main queue if needed, or mark as complete"""
        # Remove from processing queue - ignore return value
        _ = await self.redis_client.lrem(f"{self.queue_key}:processing", 1, task_id)  # type: ignore
        return True

    async def get_task_status(self, task_id: str) -> str | None:
        """Get the status of a task"""
        task = await self.get_task(task_id)
        if task:
            return task.get("status")
        return None

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task if it's still queued or processing"""
        task = await self.get_task(task_id)
        if not task:
            return False

        if task["status"] == "queued":
            # Remove from queue - ignore return value
            _ = await self.redis_client.lrem(self.queue_key, 1, task_id)  # type: ignore
            task["status"] = "cancelled"
            task["error"] = "Task was cancelled by user"
            task_key = self._get_task_key(task_id)
            await self.redis_client.set(task_key, json.dumps(task))
            logger.info(f"Task {task_id} cancelled while queued")
            return True
        elif task["status"] == "processing":
            # For processing tasks, we mark as cancelled
            # The actual processing function would need to check for cancellation
            task["status"] = "cancelled"
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
        """Check if a task has been cancelled"""
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
