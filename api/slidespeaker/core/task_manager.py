import asyncio
import uuid
from typing import Dict, Any, Optional
from pathlib import Path
from loguru import logger
from slidespeaker.core.state_manager import state_manager
from slidespeaker.core.pipeline import process_presentation

class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.task_queue = None
    
    def initialize(self):
        """Initialize the task manager with event loop"""
        if self.task_queue is None:
            self.task_queue = asyncio.Queue()
            asyncio.create_task(self._worker())
    
    def submit_task(self, task_type: str, **kwargs) -> str:
        """Submit a task and return task ID"""
        # Initialize if not already done
        if self.task_queue is None:
            self.initialize()
            
        task_id = str(uuid.uuid4())
        task = {
            "task_id": task_id,
            "task_type": task_type,
            "status": "queued",
            "kwargs": kwargs,
            "result": None,
            "error": None
        }
        self.tasks[task_id] = task
        self.task_queue.put_nowait(task_id)
        logger.info(f"Task {task_id} submitted: {task_type}")
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status by ID"""
        return self.tasks.get(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task if it's still queued or processing"""
        task = self.tasks.get(task_id)
        if not task:
            return False
            
        # If task is queued, we can remove it from the queue
        if task["status"] == "queued":
            # Note: We can't easily remove from asyncio.Queue, but we can mark it as cancelled
            task["status"] = "cancelled"
            task["error"] = "Task was cancelled by user"
            # Store cancellation status in state manager for the orchestrator to check
            import asyncio
            asyncio.create_task(self._store_task_cancellation(task_id))
            logger.info(f"Task {task_id} cancelled while queued")
            return True
        elif task["status"] == "processing":
            # For processing tasks, we mark as cancelled
            # The actual processing function would need to check for cancellation
            task["status"] = "cancelled"
            task["error"] = "Task was cancelled by user"
            # Store cancellation status in state manager for the orchestrator to check
            import asyncio
            asyncio.create_task(self._store_task_cancellation(task_id))
            logger.info(f"Task {task_id} marked as cancelled during processing")
            return True
        else:
            # Task is already completed or failed
            return False
    
    async def _store_task_cancellation(self, task_id: str):
        """Store task cancellation status in state manager"""
        try:
            from slidespeaker.core.state_manager import state_manager
            cancellation_state = {
                "task_id": task_id,
                "status": "cancelled",
                "cancelled_at": __import__('datetime').datetime.now().isoformat()
            }
            await state_manager._save_state(f"task_{task_id}", cancellation_state)
        except Exception as e:
            logger.error(f"Failed to store task cancellation status for {task_id}: {e}")
    
    async def worker_loop(self):
        """Background worker to process tasks"""
        while True:
            try:
                task_id = await self.task_queue.get()
                await self._process_task(task_id)
                self.task_queue.task_done()
            except Exception as e:
                logger.error(f"Worker error: {e}")
                
    async def _worker(self):
        """Background worker to process tasks (legacy method)"""
        await self.worker_loop()
    
    async def _process_task(self, task_id: str):
        """Process a single task"""
        task = self.tasks.get(task_id)
        if not task:
            return
        
        task["status"] = "processing"
        logger.info(f"Processing task {task_id}: {task['task_type']}")
        
        try:
            if task["task_type"] == "process_presentation":
                await self._process_presentation(task)
            else:
                raise ValueError(f"Unknown task type: {task['task_type']}")
            
            task["status"] = "completed"
            logger.info(f"Task {task_id} completed")
        except Exception as e:
            task["status"] = "failed"
            task["error"] = str(e)
            logger.error(f"Task {task_id} failed: {e}")
    
    async def _process_presentation(self, task: Dict[str, Any]):
        """Process presentation task"""
        task_id = task.get("task_id")
        kwargs = task["kwargs"]
        file_id = kwargs.get("file_id")
        file_path = kwargs.get("file_path")
        file_ext = kwargs.get("file_ext")
        
        if not file_id or not file_path or not file_ext:
            raise ValueError("Missing required parameters for presentation processing")
        
        # Call the orchestrator processing function
        try:
            language = task.get("kwargs", {}).get("language", "english")
            subtitle_language = task.get("kwargs", {}).get("subtitle_language")
            generate_avatar = task.get("kwargs", {}).get("generate_avatar", True)
            generate_subtitles = task.get("kwargs", {}).get("generate_subtitles", True)
            await process_presentation(file_id, Path(file_path), file_ext, language, subtitle_language, generate_avatar, generate_subtitles, task_id=task_id)
            task["result"] = {
                "file_id": file_id,
                "status": "completed"
            }
        except Exception as e:
            logger.error(f"Presentation processing failed for {file_id}: {e}")
            raise

# Global task manager instance
task_manager = TaskManager()