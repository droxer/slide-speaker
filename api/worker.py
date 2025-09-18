#!/usr/bin/env python3
"""
Worker process for SlideSpeaker AI processing tasks.
This script is spawned by the master worker to process individual tasks.
It handles the complete presentation processing pipeline for a single task.
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

from slidespeaker.configs.config import config, get_env  # noqa: E402
from slidespeaker.configs.logging_config import setup_logging  # noqa: E402

log_file = config.log_file
setup_logging(
    config.log_level,
    log_file,
    enable_file_logging=log_file is not None,
    component="worker",
)

from slidespeaker.core.task_queue import task_queue  # noqa: E402
from slidespeaker.pipeline.coordinator import accept_task  # noqa: E402


class TaskProgressMonitor:
    """Monitor task progress and update status periodically"""

    def __init__(self, task_id: str):
        """Initialize the progress monitor for a specific task"""
        self.task_id = task_id
        self.monitoring = True

    async def monitor_progress(self) -> None:
        """Monitor task progress and log updates"""
        check_count = 0
        last_status = None
        while self.monitoring:
            try:
                # Get current task status
                task = await task_queue.get_task(self.task_id)
                if task and "status" in task:
                    check_count += 1

                    # Log status changes
                    current_status = task["status"]
                    if current_status != last_status:
                        logger.info(
                            f"Task {self.task_id} status changed from '{last_status}' to '{current_status}'"
                        )
                        last_status = current_status

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
    """Process a single task by ID through the complete presentation pipeline"""
    logger.info(f"Worker starting to process task {task_id}")

    # Get task details from Redis
    task = await task_queue.get_task(task_id)
    if not task:
        logger.error(f"Task {task_id} not found in Redis")
        return False

    logger.info(
        f"Task {task_id} retrieved from Redis with status: {task.get('status', 'unknown')}"
    )

    if task["status"] == "cancelled":
        logger.info(f"Task {task_id} was cancelled, skipping processing")
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
        voice_language = kwargs.get("voice_language", "english")
        subtitle_language = kwargs.get("subtitle_language")
        transcript_language = kwargs.get("transcript_language")
        generate_avatar = kwargs.get("generate_avatar", True)
        generate_subtitles = True  # Always generate subtitles
        generate_podcast = kwargs.get("generate_podcast", False)
        generate_video = kwargs.get("generate_video", True)

        logger.info(
            f"Task {task_id} parameters extracted - file_id: {file_id}, "
            f"file_ext: {file_ext}, voice_language: {voice_language}, "
            f"subtitle_language: {subtitle_language}, "
            f"generate_avatar: {generate_avatar}, "
            f"generate_podcast: {generate_podcast}, "
            f"generate_video: {generate_video}"
        )

        # Validate required parameters
        missing_params = []
        if not file_id:
            missing_params.append("file_id")
        if not file_path:
            missing_params.append("file_path")
        if not file_ext:
            missing_params.append("file_ext")

        if missing_params:
            error_msg = f"Missing required parameters for presentation processing: {', '.join(missing_params)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Log file path security check
        if file_path and not os.path.exists(file_path):
            logger.warning(f"File path does not exist: {file_path}")

        # Process the presentation
        logger.info(
            f"Task {task_id} starting presentation processing for file {file_id}"
        )
        await accept_task(
            file_id=file_id,
            file_path=Path(file_path),
            file_ext=file_ext,
            voice_language=voice_language,
            subtitle_language=subtitle_language,
            transcript_language=transcript_language,
            generate_avatar=generate_avatar,
            generate_subtitles=generate_subtitles,
            generate_podcast=generate_podcast,
            generate_video=generate_video,
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
    """Main worker process entry point"""
    # Get task ID from environment variable
    task_id = get_env("TASK_ID")
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
