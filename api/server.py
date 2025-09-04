import asyncio
import base64
import hashlib
import os
from pathlib import Path
from typing import Any

import aiofiles
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from loguru import logger

from slidespeaker.core.state_manager import state_manager
from slidespeaker.core.task_queue import task_queue
from slidespeaker.utils.config import config
from slidespeaker.utils.locales import locale_utils

app = FastAPI(title="AI Slider API")


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize on startup"""
    pass


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = config.uploads_dir
OUTPUT_DIR = config.output_dir


@app.post("/api/upload")
async def upload_file(request: Request) -> dict[str, str | None]:
    try:
        # Parse JSON data from request body
        body = await request.json()
        filename = body.get("filename")
        file_data = body.get("file_data")
        language = body.get("language", "english")
        subtitle_language = body.get(
            "subtitle_language"
        )  # Don't default to audio language
        generate_avatar = body.get("generate_avatar", True)  # Default to True
        generate_subtitles = True  # Always generate subtitles by default

        if not filename or not file_data:
            raise HTTPException(
                status_code=400, detail="Filename and file data are required"
            )

        # Decode base64 file data
        file_bytes = base64.b64decode(file_data)

        file_ext = Path(filename).suffix.lower()
        if file_ext not in [".pdf", ".pptx", ".ppt"]:
            raise HTTPException(
                status_code=400, detail="Only PDF and PowerPoint files are supported"
            )

        # Validate languages
        if not locale_utils.validate_language(language):
            raise HTTPException(
                status_code=400, detail=f"Unsupported audio language: {language}"
            )

        if subtitle_language and not locale_utils.validate_language(subtitle_language):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported subtitle language: {subtitle_language}",
            )

        # Generate hash-based ID
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        file_id = file_hash[:16]  # Use first 16 chars of hash
        file_path = UPLOAD_DIR / f"{file_id}{file_ext}"

        # Write file to disk
        async with aiofiles.open(file_path, "wb") as out_file:
            await out_file.write(file_bytes)

        # Create initial state
        await state_manager.create_state(
            file_id,
            file_path,
            file_ext,
            language,
            subtitle_language,
            generate_avatar,
            generate_subtitles,
        )

        # Submit task to Redis task queue
        task_id = await task_queue.submit_task(
            "process_presentation",
            file_id=file_id,
            file_path=str(file_path),
            file_ext=file_ext,
            language=language,
            subtitle_language=subtitle_language,
            generate_avatar=generate_avatar,
            generate_subtitles=generate_subtitles,
        )

        logger.info(
            f"File uploaded: {file_id}, type: {file_ext}, task submitted: {task_id}"
        )

        return {
            "file_id": file_id,
            "task_id": task_id,
            "message": "File uploaded successfully, processing started in background",
        }

    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}") from e


@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str) -> dict[str, Any]:
    """Get task status by ID"""
    task_status = await task_queue.get_task(task_id)
    if not task_status:
        raise HTTPException(status_code=404, detail="Task not found")

    return task_status


@app.post("/api/task/{task_id}/cancel")
async def cancel_task(task_id: str) -> dict[str, str]:
    """Cancel a task"""
    try:
        success = await task_queue.cancel_task(task_id)
        if success:
            return {"message": "Task cancelled successfully"}
        else:
            raise HTTPException(
                status_code=400,
                detail="Task cannot be cancelled (already completed or not found)",
            )
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to cancel task: {str(e)}"
        ) from e


@app.get("/api/progress/{file_id}")
async def get_progress(file_id: str) -> dict[str, Any]:
    """Get detailed progress information including current step and status"""
    state = await state_manager.get_state(file_id)

    if not state:
        return {
            "status": "not_found",
            "message": "File not found or processing not started",
            "progress": 0,
            "current_step": "unknown",
            "steps": {},
        }

    # Calculate overall progress percentage
    # Total steps can vary based on whether subtitle steps are included
    total_steps = len(
        [step for step in state["steps"].values() if step["status"] != "skipped"]
    )
    completed_steps = sum(
        1 for step in state["steps"].values() if step["status"] == "completed"
    )
    progress_percentage = (
        int((completed_steps / total_steps) * 100) if total_steps > 0 else 0
    )

    return {
        "status": state["status"],
        "progress": progress_percentage,
        "current_step": state["current_step"],
        "steps": state["steps"],
        "errors": state["errors"],
        "created_at": state["created_at"],
        "updated_at": state["updated_at"],
    }


@app.get("/api/video/{file_id}")
async def get_video(file_id: str) -> FileResponse:
    video_path = OUTPUT_DIR / f"{file_id}_final.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")

    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"presentation_{file_id}.mp4",
        headers={
            "Content-Disposition": f"attachment; filename=presentation_{file_id}.mp4"
        },
    )


@app.get("/api/subtitles/{file_id}/srt")
async def get_srt_subtitles(file_id: str) -> FileResponse:
    srt_path = OUTPUT_DIR / f"{file_id}_final.srt"
    if not srt_path.exists():
        raise HTTPException(status_code=404, detail="SRT subtitles not found")

    return FileResponse(
        srt_path,
        media_type="text/plain",
        filename=f"presentation_{file_id}.srt",
        headers={
            "Content-Disposition": f"attachment; filename=presentation_{file_id}.srt"
        },
    )


@app.get("/api/subtitles/{file_id}/vtt")
async def get_vtt_subtitles(file_id: str) -> FileResponse:
    vtt_path = OUTPUT_DIR / f"{file_id}_final.vtt"
    if not vtt_path.exists():
        raise HTTPException(status_code=404, detail="VTT subtitles not found")

    return FileResponse(
        vtt_path,
        media_type="text/vtt",
        filename=f"presentation_{file_id}.vtt",
        headers={
            "Content-Disposition": f"inline; filename=presentation_{file_id}.vtt",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


@app.get("/api/languages")
async def get_supported_languages() -> list[dict[str, str]]:
    """
    Get list of all supported languages with locale codes and display names
    """
    return locale_utils.get_supported_languages()


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "AI Slider Backend API"}


if __name__ == "__main__":
    import asyncio
    import signal

    import uvicorn

    # Create an event to signal shutdown
    shutdown_event = asyncio.Event()

    def signal_handler(sig: int, frame: Any) -> None:
        print("\nReceived shutdown signal, stopping server...")
        shutdown_event.set()

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the server with shutdown handling
    port = int(os.getenv("PORT", "8000"))
    uvicorn_config = uvicorn.Config(app, host="0.0.0.0", port=port)
    server = uvicorn.Server(uvicorn_config)

    async def run_server() -> None:
        await server.serve()
        # When server stops, set the shutdown event
        shutdown_event.set()

    async def main() -> None:
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
