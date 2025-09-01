import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import redis.asyncio as redis
from dotenv import load_dotenv
import os
from loguru import logger

load_dotenv()

class RedisStateManager:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_DB', 0)),
            password=os.getenv('REDIS_PASSWORD', None),
            decode_responses=True,
            socket_timeout=5.0  # Add timeout to prevent hanging
        )
    
    def _get_key(self, file_id: str) -> str:
        return f"ai_slider:state:{file_id}"
    
    async def create_state(self, file_id: str, file_path: Path, file_ext: str) -> Dict[str, Any]:
        """Create initial state for a file processing"""
        state = {
            "file_id": file_id,
            "file_path": str(file_path),
            "file_ext": file_ext,
            "status": "uploaded",
            "current_step": "extract_slides",
            "steps": {
                "extract_slides": {"status": "pending", "data": None},
                "convert_slides_to_images": {"status": "pending", "data": None},
                "analyze_slide_images": {"status": "pending", "data": None},
                "generate_scripts": {"status": "pending", "data": None},
                "review_scripts": {"status": "pending", "data": None},
                "generate_audio": {"status": "pending", "data": None},
                "generate_avatar_videos": {"status": "pending", "data": None},
                "compose_video": {"status": "pending", "data": None}
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "errors": []
        }
        await self._save_state(file_id, state)
        return state
    
    async def get_state(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get current state for a file"""
        key = self._get_key(file_id)
        state_json = await self.redis_client.get(key)
        if state_json:
            return json.loads(state_json)
        return None
    
    async def update_step_status(self, file_id: str, step_name: str, status: str, data: Any = None):
        """Update status of a specific step"""
        state = await self.get_state(file_id)
        if state:
            state["steps"][step_name]["status"] = status
            if data is not None:
                state["steps"][step_name]["data"] = data
            state["updated_at"] = datetime.now().isoformat()
            state["current_step"] = step_name
            await self._save_state(file_id, state)
    
    async def add_error(self, file_id: str, error: str, step: str):
        """Add error to state"""
        state = await self.get_state(file_id)
        if state:
            state["errors"].append({
                "step": step,
                "error": error,
                "timestamp": datetime.now().isoformat()
            })
            state["updated_at"] = datetime.now().isoformat()
            await self._save_state(file_id, state)
    
    async def mark_completed(self, file_id: str):
        """Mark processing as completed"""
        state = await self.get_state(file_id)
        if state:
            state["status"] = "completed"
            state["updated_at"] = datetime.now().isoformat()
            await self._save_state(file_id, state)
    
    async def mark_failed(self, file_id: str):
        """Mark processing as failed"""
        state = await self.get_state(file_id)
        if state:
            state["status"] = "failed"
            state["updated_at"] = datetime.now().isoformat()
            await self._save_state(file_id, state)
    
    async def get_next_step(self, file_id: str) -> Optional[str]:
        """Get the next step that needs to be processed"""
        state = await self.get_state(file_id)
        if state:
            steps_order = [
                "extract_slides",
                "convert_slides_to_images",
                "analyze_slide_images",
                "generate_scripts", 
                "review_scripts",
                "generate_audio",
                "generate_avatar_videos",
                "compose_video"
            ]
            
            # First check if there's a step that's currently processing (might have been interrupted)
            for step in steps_order:
                if state["steps"][step]["status"] == "processing":
                    return step
            
            # Then look for pending or failed steps
            for step in steps_order:
                if state["steps"][step]["status"] in ["pending", "failed"]:
                    return step
            
            # If all steps are completed, return None
            return None
        return None
    
    async def _save_state(self, file_id: str, state: Dict[str, Any]):
        """Save state to Redis"""
        key = self._get_key(file_id)
        await self.redis_client.set(key, json.dumps(state), ex=86400)  # 24h expiration
    
    async def cleanup_state(self, file_id: str):
        """Remove state from Redis"""
        key = self._get_key(file_id)
        await self.redis_client.delete(key)

# Global state manager instance
state_manager = RedisStateManager()