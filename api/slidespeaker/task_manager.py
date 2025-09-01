import asyncio
import uuid
from typing import Dict, Any, Optional
from pathlib import Path
from loguru import logger
from slidespeaker.state_manager import state_manager
from slidespeaker.orchestrator import process_presentation

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
    
    async def _worker(self):
        """Background worker to process tasks"""
        while True:
            try:
                task_id = await self.task_queue.get()
                await self._process_task(task_id)
                self.task_queue.task_done()
            except Exception as e:
                logger.error(f"Worker error: {e}")
    
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
        kwargs = task["kwargs"]
        file_id = kwargs.get("file_id")
        file_path = kwargs.get("file_path")
        file_ext = kwargs.get("file_ext")
        
        if not file_id or not file_path or not file_ext:
            raise ValueError("Missing required parameters for presentation processing")
        
        # Call the orchestrator processing function
        try:
            language = task.get("kwargs", {}).get("language", "english")
            await process_presentation(file_id, Path(file_path), file_ext, language)
            task["result"] = {
                "file_id": file_id,
                "status": "completed"
            }
        except Exception as e:
            logger.error(f"Presentation processing failed for {file_id}: {e}")
            raise

# Global task manager instance
task_manager = TaskManager()