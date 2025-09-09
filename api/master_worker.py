#!/usr/bin/env python3
"""
Master Worker for SlideSpeaker AI processing tasks.
This script polls Redis for tasks and dispatches them to worker processes.
It manages the lifecycle of worker processes and ensures proper task distribution.
"""

import asyncio
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file
load_dotenv()

# Add the current directory to Python path so we can import slidespeaker modules
sys.path.insert(0, str(Path(__file__).parent))

from slidespeaker.utils.logging_config import setup_logging  # noqa: E402

log_level = os.getenv("LOG_LEVEL", "INFO")
log_file = os.getenv("LOG_FILE")
setup_logging(
    log_level,
    log_file,
    enable_file_logging=log_file is not None,
    component="master_worker",
)

from slidespeaker.core.task_queue import task_queue  # noqa: E402


class MasterWorker:
    """Master worker that manages task distribution to worker processes"""

    def __init__(self) -> None:
        """Initialize the master worker with configuration settings"""
        self.should_stop = False
        self.workers: list[subprocess.Popen[bytes]] = []
        self.max_workers = int(os.getenv("MAX_WORKERS", "2"))  # Default to 3 workers
        self.worker_processes: dict[str, subprocess.Popen[bytes]] = {}

    def signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals gracefully"""
        logger.info("Received shutdown signal, stopping master worker...")
        self.should_stop = True

    def start_worker_process(self, task_id: str) -> subprocess.Popen[bytes]:
        """Start a new worker process for a specific task"""
        worker_script = Path(__file__).parent / "worker.py"
        env = os.environ.copy()
        env["TASK_ID"] = task_id

        # Start worker process with stdout/stderr inherited from parent for real-time logging
        process = subprocess.Popen(
            [sys.executable, str(worker_script)],
            env=env,
        )

        self.worker_processes[task_id] = process
        logger.info(
            f"Started worker process for task {task_id} with PID {process.pid}, "
            f"total workers now: {len(self.worker_processes)}/{self.max_workers}"
        )
        return process

    def cleanup_workers(self) -> None:
        """Clean up all worker processes"""
        if not self.worker_processes:
            logger.debug("No worker processes to clean up")
            return

        logger.info(f"Cleaning up {len(self.worker_processes)} worker processes")

        for task_id, process in self.worker_processes.items():
            if process.poll() is None:  # Process is still running
                logger.info(f"Terminating worker for task {task_id}")
                process.terminate()

        # Wait for processes to terminate
        for task_id, process in self.worker_processes.items():
            try:
                process.wait(timeout=5)
                logger.info(f"Worker for task {task_id} terminated successfully")
            except subprocess.TimeoutExpired:
                logger.warning(
                    f"Worker for task {task_id} did not terminate within timeout, killing..."
                )
                process.kill()
                process.wait()
                logger.info(f"Worker for task {task_id} killed forcefully")

    async def run(self) -> None:
        """Run the master worker main loop"""
        logger.info("Starting master worker...")
        logger.info(f"Will manage up to {self.max_workers} worker processes")

        # Test Redis connection
        try:
            ping_result = await task_queue.redis_client.ping()
            logger.info(f"Master worker Redis ping result: {ping_result}")

            # Log Redis config
            config_info = task_queue.redis_client.connection_pool.connection_kwargs
            logger.info(f"Master worker Redis config: {config_info}")

            # Check for existing tasks
            keys = await task_queue.redis_client.keys("ss:task:*")
            logger.info(f"Found {len(keys)} existing task keys")

            queue_items = await task_queue.redis_client.lrange("ss:task_queue", 0, -1)  # type: ignore
            logger.info(f"Found {len(queue_items)} items in task queue")

        except Exception as e:
            logger.error(f"Master worker Redis connection error: {e}")
            logger.error("Cannot continue without Redis connection. Exiting...")
            return

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        try:
            while not self.should_stop:
                # Log current worker status
                active_workers = len(self.worker_processes)
                logger.info(
                    f"Master worker status: {active_workers}/{self.max_workers} workers active, "
                    f"tasks in progress: {list(self.worker_processes.keys())}"
                )

                # Check for completed workers
                await self.check_completed_workers()

                # If we have capacity, look for new tasks
                active_workers = len(self.worker_processes)
                if active_workers < self.max_workers:
                    logger.debug(
                        f"Worker capacity available: {active_workers}/{self.max_workers}"
                    )
                    task_id = await task_queue.get_next_task()
                    if task_id:
                        # Check if task is cancelled before starting worker
                        task = await task_queue.get_task(task_id)
                        if task and task.get("status") == "cancelled":
                            logger.info(f"Skipping cancelled task {task_id}")
                            await task_queue.complete_task_processing(task_id)
                            continue

                        logger.info(f"Found task {task_id}, starting worker process")
                        await task_queue.update_task_status(task_id, "processing")

                        # Small delay to ensure task is fully committed to Redis
                        await asyncio.sleep(0.5)

                        self.start_worker_process(task_id)
                        logger.info(f"Worker process started for task {task_id}")
                    else:
                        # No tasks available, sleep briefly
                        logger.debug("No tasks available in queue, waiting...")
                else:
                    # At max capacity, just check for completed workers
                    logger.debug(
                        "At maximum worker capacity, checking for completions..."
                    )
                    await self.check_completed_workers()
                    await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Master worker encountered an error: {e}")
        finally:
            logger.info("Shutting down master worker...")
            self.cleanup_workers()
            logger.info("Master worker shutdown complete")

    async def check_completed_workers(self) -> None:
        """Check for completed worker processes and clean them up"""
        completed_tasks = []
        for task_id, process in list(self.worker_processes.items()):
            if process.poll() is not None:  # Process has completed
                logger.info(
                    f"Worker for task {task_id} completed with "
                    f"return code {process.returncode}"
                )
                completed_tasks.append(task_id)

                # Update task status based on return code
                if process.returncode == 0:
                    await task_queue.update_task_status(task_id, "completed")
                    logger.info(f"Task {task_id} marked as completed successfully")
                else:
                    await task_queue.update_task_status(
                        task_id,
                        "failed",
                        error=f"Worker failed with return code {process.returncode}",
                    )
                    logger.error(
                        f"Task {task_id} marked as failed with return code {process.returncode}"
                    )

        # Remove completed workers
        for task_id in completed_tasks:
            del self.worker_processes[task_id]
            logger.info(f"Removed completed worker for task {task_id}")


if __name__ == "__main__":
    master = MasterWorker()
    try:
        asyncio.run(master.run())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Master worker failed to start: {e}")
        sys.exit(1)
