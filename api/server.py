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

from slidespeaker.routes.downloads import router as downloads_router
from slidespeaker.routes.languages import router as languages_router
from slidespeaker.routes.progress import router as progress_router
from slidespeaker.routes.stats import router as stats_router
from slidespeaker.routes.tasks import router as tasks_router
from slidespeaker.routes.upload import router as upload_router
from slidespeaker.utils.config import config
from slidespeaker.utils.logging_config import setup_logging

app = FastAPI(title="AI Slider API")


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize logging configuration on application startup"""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_file = os.getenv("LOG_FILE")
    setup_logging(
        log_level, log_file, enable_file_logging=log_file is not None, component="api"
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
app.include_router(upload_router)
app.include_router(tasks_router)
app.include_router(progress_router)
app.include_router(downloads_router)
app.include_router(languages_router)
app.include_router(stats_router)


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
