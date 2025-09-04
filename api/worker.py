#!/usr/bin/env python3
"""
Worker process for SlideSpeaker AI processing tasks.
This script is spawned by the master worker to process individual tasks.
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file
load_dotenv()

# Add the current directory to Python path so we can import slidespeaker modules
sys.path.insert(0, str(Path(__file__).parent))

from slidespeaker.core.task_queue import task_queue  # noqa: E402
from slidespeaker.pipeline.coordinator import process_presentation  # noqa: E402

# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="{time} | {level} | {name}:{function}:{line} - {message}",
    level="INFO",
)


class TaskProgressMonitor:
    """Monitor task progress and update status periodically"""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.monitoring = True

    async def monitor_progress(self) -> None:
        """Monitor task progress and log updates"""
        check_count = 0
        while self.monitoring:
            try:
                # Get current task status
                task = await task_queue.get_task(self.task_id)
                if task and "status" in task:
                    check_count += 1

                    # Log detailed status every 5 checks (every 25 seconds)
                    if check_count % 5 == 0:
                        logger.info(
                            f"Task {self.task_id} status check #{check_count}: {task['status']}, "
                            f"updated at: {task.get('updated_at', 'unknown')}"
                        )
                    else:
                        logger.debug(f"Task {self.task_id} status: {task['status']}")

                    # If task is cancelled, stop monitoring
                    if task.get("status") == "cancelled":
                        logger.info(
                            f"Task {self.task_id} was cancelled, stopping monitoring"
                        )
                        break

                    # Also check for immediate cancellation
                    if await task_queue.is_task_cancelled(self.task_id):
                        logger.info(
                            f"Task {self.task_id} was cancelled (immediate check), "
                            f"stopping monitoring"
                        )
                        break

                # Wait before next check
                await asyncio.sleep(5)  # Check every 5 seconds for faster response

            except Exception as e:
                logger.error(f"Error monitoring task {self.task_id}: {e}")
                break

    def stop_monitoring(self) -> None:
        """Stop monitoring task progress"""
        self.monitoring = False


async def process_task(task_id: str) -> bool:
    """Process a single task by ID"""
    logger.info(f"Worker starting to process task {task_id}")

    # Get task details from Redis
    task = await task_queue.get_task(task_id)
    if not task:
        logger.error(f"Task {task_id} not found")
        return False

    if task["status"] == "cancelled":
        logger.info(f"Task {task_id} was cancelled, skipping")
        return True

    # Start progress monitoring
    progress_monitor = TaskProgressMonitor(task_id)
    monitor_task = asyncio.create_task(progress_monitor.monitor_progress())

    try:
        # Update task status to processing
        await task_queue.update_task_status(task_id, "processing")
        logger.info(f"Task {task_id} status updated to processing")

        # Extract task parameters
        kwargs = task.get("kwargs", {})
        file_id = kwargs.get("file_id")
        file_path = kwargs.get("file_path")
        file_ext = kwargs.get("file_ext")
        language = kwargs.get("language", "english")
        subtitle_language = kwargs.get("subtitle_language")
        generate_avatar = kwargs.get("generate_avatar", True)
        generate_subtitles = True  # Always generate subtitles

        logger.info(
            f"Task {task_id} parameters extracted - file_id: {file_id}, "
            f"file_ext: {file_ext}, language: {language}, "
            f"subtitle_language: {subtitle_language}, generate_avatar: {generate_avatar}"
        )

        if not file_id or not file_path or not file_ext:
            raise ValueError("Missing required parameters for presentation processing")

        # Process the presentation
        logger.info(
            f"Task {task_id} starting presentation processing for file {file_id}"
        )
        await process_presentation(
            file_id,
            Path(file_path),
            file_ext,
            language,
            subtitle_language,
            generate_avatar,
            generate_subtitles,
            task_id=task_id,
        )

        logger.info(f"Task {task_id} completed successfully")
        return True

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        await task_queue.update_task_status(task_id, "failed", error=str(e))
        return False
    finally:
        # Stop progress monitoring
        progress_monitor.stop_monitoring()
        if not monitor_task.done():
            monitor_task.cancel()


async def main() -> None:
    """Main worker process"""
    # Get task ID from environment variable
    task_id = os.getenv("TASK_ID")
    if not task_id:
        logger.error("TASK_ID environment variable not set")
        sys.exit(1)

    logger.info(f"Task worker starting for task {task_id}")

    try:
        success = await process_task(task_id)
        if success:
            await task_queue.update_task_status(task_id, "completed")
            await task_queue.complete_task_processing(task_id)
            logger.info(f"Task worker completed successfully for task {task_id}")
            sys.exit(0)
        else:
            logger.error(f"Task worker failed for task {task_id}")
            await task_queue.complete_task_processing(task_id)
            sys.exit(1)
    except Exception as e:
        logger.error(f"Task worker encountered unexpected error: {e}")
        await task_queue.update_task_status(task_id, "failed", error=str(e))
        await task_queue.complete_task_processing(task_id)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
