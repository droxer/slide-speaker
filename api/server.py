"""
Main FastAPI server module for SlideSpeaker.
This module initializes the FastAPI application, configures routes, CORS middleware,
and handles graceful server startup and shutdown.
"""

import asyncio
import os
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from slidespeaker.configs.config import config
from slidespeaker.configs.logging_config import setup_logging
from slidespeaker.routes.audio_downloads import router as audio_downloads_router
from slidespeaker.routes.auth import router as auth_router
from slidespeaker.routes.diagnostic import router as diagnostic_router
from slidespeaker.routes.downloads import router as downloads_router
from slidespeaker.routes.files import router as files_router
from slidespeaker.routes.health import router as health_router
from slidespeaker.routes.languages import router as languages_router
from slidespeaker.routes.podcast_downloads import router as podcast_downloads_router
from slidespeaker.routes.preview import router as preview_router
from slidespeaker.routes.progress import router as progress_router
from slidespeaker.routes.stats import router as stats_router
from slidespeaker.routes.subtitle_downloads import router as subtitle_downloads_router
from slidespeaker.routes.tasks import router as tasks_router
from slidespeaker.routes.transcripts import router as transcripts_router
from slidespeaker.routes.tts import router as tts_router
from slidespeaker.routes.upload import router as upload_router
from slidespeaker.routes.video_downloads import router as video_downloads_router

app = FastAPI(title="AI Slider API")


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize logging configuration on application startup"""
    # Use centralized config for logging settings
    log_level = config.log_level
    log_file = config.log_file
    setup_logging(
        log_level,
        log_file,
        enable_file_logging=log_file is not None,
        component="api",
    )

    # Mount static files for local storage if using local storage provider
    if config.storage_provider == "local":
        # Ensure the storage directory exists
        config.output_dir.mkdir(parents=True, exist_ok=True)
        # Mount the storage directory at /files/ path
        app.mount("/files", StaticFiles(directory=config.output_dir), name="files")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all route modules
app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(files_router)
app.include_router(tasks_router)
app.include_router(progress_router)
app.include_router(downloads_router)
app.include_router(video_downloads_router)
app.include_router(audio_downloads_router)
app.include_router(subtitle_downloads_router)
app.include_router(podcast_downloads_router)
app.include_router(languages_router)
app.include_router(health_router)
app.include_router(stats_router)
app.include_router(transcripts_router)
app.include_router(tts_router)
app.include_router(diagnostic_router)
app.include_router(preview_router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint that returns a welcome message"""
    return {"message": "SlideSpeaker Backend API"}


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
