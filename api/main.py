from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import os
import uuid
import asyncio
import hashlib
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
import aiofiles
from loguru import logger

from slidespeaker.state_manager import state_manager
from slidespeaker.task_manager import task_manager
from slidespeaker.orchestrator import run

load_dotenv()

app = FastAPI(title="AI Slider API")

@app.on_event("startup")
async def startup_event():
    """Initialize task manager on startup"""
    task_manager.initialize()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("output")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), language: str = "english"):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ['.pdf', '.pptx', '.ppt']:
        raise HTTPException(status_code=400, detail="Only PDF and PowerPoint files are supported")
    
    # Read file content and generate hash-based ID
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()
    file_id = file_hash[:16]  # Use first 16 chars of hash
    file_path = UPLOAD_DIR / f"{file_id}{file_ext}"
    
    # Write file to disk
    async with aiofiles.open(file_path, 'wb') as out_file:
        await out_file.write(content)
    
    # Create initial state
    await state_manager.create_state(file_id, file_path, file_ext)
    
    # Submit task to task manager
    task_id = task_manager.submit_task(
        "process_presentation",
        file_id=file_id,
        file_path=str(file_path),
        file_ext=file_ext,
        language=language
    )
    
    logger.info(f"File uploaded: {file_id}, type: {file_ext}, task submitted: {task_id}")
    
    return {
        "file_id": file_id,
        "task_id": task_id,
        "message": "File uploaded successfully, processing started in background"
    }


@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    """Get task status by ID"""
    task_status = task_manager.get_task_status(task_id)
    if not task_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task_status

@app.get("/api/progress/{file_id}")
async def get_progress(file_id: str):
    """Get detailed progress information including current step and status"""
    state = await state_manager.get_state(file_id)
    
    if not state:
        return {
            "status": "not_found", 
            "message": "File not found or processing not started",
            "progress": 0,
            "current_step": "unknown",
            "steps": {}
        }
    
    # Calculate overall progress percentage
    total_steps = 8  # extract_slides, convert_slides_to_images, analyze_slide_images, generate_scripts, review_scripts, generate_audio, generate_avatar_videos, compose_video
    completed_steps = sum(1 for step in state["steps"].values() if step["status"] == "completed")
    progress_percentage = int((completed_steps / total_steps) * 100)
    
    return {
        "status": state["status"],
        "progress": progress_percentage,
        "current_step": state["current_step"],
        "steps": state["steps"],
        "errors": state["errors"],
        "created_at": state["created_at"],
        "updated_at": state["updated_at"]
    }

@app.get("/api/video/{file_id}")
async def get_video(file_id: str):
    video_path = OUTPUT_DIR / f"{file_id}_final.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    
    return FileResponse(video_path, media_type="video/mp4", filename=f"presentation_{file_id}.mp4")

@app.get("/")
async def root():
    return {"message": "AI Slider Backend API"}

if __name__ == "__main__":
    import uvicorn
    import signal
    import asyncio
    
    # Create an event to signal shutdown
    shutdown_event = asyncio.Event()
    
    def signal_handler(sig, frame):
        print("\nReceived shutdown signal, stopping server...")
        shutdown_event.set()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the server with shutdown handling
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    
    async def run_server():
        await server.serve()
        # When server stops, set the shutdown event
        shutdown_event.set()
    
    async def main():
        # Run server in background task
        server_task = asyncio.create_task(run_server())
        
        # Wait for shutdown signal
        await shutdown_event.wait()
        
        # Stop the server
        server.should_exit = True
        await server.shutdown()
        
        # Wait for server task to complete
        await server_task
        
        # Clean up any remaining background tasks
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        
        # Wait for tasks to be cancelled
        await asyncio.gather(*tasks, return_exceptions=True)
        
    asyncio.run(main())