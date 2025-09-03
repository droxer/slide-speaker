#!/usr/bin/env python3
"""
Master Worker for SlideSpeaker AI processing tasks.
This script polls Redis for tasks and dispatches them to worker processes.
"""

import asyncio
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

from loguru import logger

# Add the current directory to Python path so we can import slidespeaker modules
sys.path.insert(0, str(Path(__file__).parent))

from slidespeaker.core.task_queue import task_queue

# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="{time} | {level} | {name}:{function}:{line} - {message}",
    level="INFO",
)


class MasterWorker:
    def __init__(self) -> None:
        self.should_stop = False
        self.workers: list[subprocess.Popen[bytes]] = []
        self.max_workers = int(os.getenv("MAX_WORKERS", "3"))  # Default to 3 workers
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

        process = subprocess.Popen(
            [sys.executable, str(worker_script)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.worker_processes[task_id] = process
        logger.info(f"Started worker process for task {task_id} with PID {process.pid}")
        return process

    def cleanup_workers(self) -> None:
        """Clean up all worker processes"""
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
                    f"Worker for task {task_id} did not terminate, killing..."
                )
                process.kill()
                process.wait()

    async def run(self) -> None:
        """Run the master worker"""
        logger.info("Starting master worker...")
        logger.info(f"Will manage up to {self.max_workers} worker processes")

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        try:
            while not self.should_stop:
                # Check for completed workers
                await self.check_completed_workers()

                # If we have capacity, look for new tasks
                if len(self.worker_processes) < self.max_workers:
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
                        self.start_worker_process(task_id)
                    else:
                        # No tasks available, sleep briefly
                        await asyncio.sleep(1)
                else:
                    # At max capacity, just check for completed workers
                    await self.check_completed_workers()
                    await asyncio.sleep(1)

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
                # Get output
                stdout, stderr = process.communicate()
                if stdout:
                    logger.info(f"Worker stdout for task {task_id}: {stdout.decode()}")
                if stderr:
                    logger.error(f"Worker stderr for task {task_id}: {stderr.decode()}")

                logger.info(
                    f"Worker for task {task_id} completed with "
                    f"return code {process.returncode}"
                )
                completed_tasks.append(task_id)

                # Update task status based on return code
                if process.returncode == 0:
                    await task_queue.update_task_status(task_id, "completed")
                else:
                    await task_queue.update_task_status(
                        task_id,
                        "failed",
                        error=f"Worker failed with return code {process.returncode}",
                    )

        # Remove completed workers
        for task_id in completed_tasks:
            del self.worker_processes[task_id]


if __name__ == "__main__":
    master = MasterWorker()
    try:
        asyncio.run(master.run())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Master worker failed to start: {e}")
        sys.exit(1)
