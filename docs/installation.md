# Installation Guide

## Prerequisites

- Python 3.12+
- Node.js 16+
- Redis server
- FFmpeg
- API keys for:
  - OpenAI
  - ElevenLabs
  - HeyGen

## Backend Setup

1. Navigate to the API directory:
   ```bash
   cd api
   ```

2. Install Python dependencies:
   ```bash
   uv sync
   ```

3. Create a `.env` file in the `api/` directory:
   ```env
   OPENAI_API_KEY=your_openai_api_key
   ELEVENLABS_API_KEY=your_elevenlabs_api_key
   HEYGEN_API_KEY=your_heygen_api_key
   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_PASSWORD=your_redis_password_or_empty
   ```

4. Start Redis:
   ```bash
   # On macOS with Homebrew
   brew services start redis

   # Or using the provided Makefile
   make redis-start
   ```

5. Start the API server and background workers:
   ```bash
   # Development mode (API server with embedded worker)
   make dev

   # Production mode (distributed architecture - recommended)
   # Terminal 1:
   make start
   # Terminal 2:
   make master-worker
   
   # Alternative: Standalone worker mode (for simpler deployments)
   # Terminal 1:
   STANDALONE_WORKER=true make start
   # Terminal 2:
   make worker
   ```

6. Alternatively, start components directly:
   ```bash
   # API server only (with embedded worker)
   uv run python server.py
   
   # Master worker (in separate terminal - recommended for production)
   uv run python master_worker.py
   
   # Standalone worker (in separate terminal - alternative approach)
   STANDALONE_WORKER=true uv run python worker.py
   ```

## Frontend Setup

1. Navigate to the web directory:
   ```bash
   cd web
   ```

2. Install Node.js dependencies:
   ```bash
   npm install  # or pnpm install
   ```

3. Start the development server:
   ```bash
   npm start    # or pnpm start
   ```

The frontend will be available at `http://localhost:3000` and automatically proxy API requests to the backend at `http://localhost:8000`.

## Task Cancellation

SlideSpeaker now features improved task cancellation that allows users to immediately stop processing tasks. When a task is cancelled:

- Queued tasks are removed from the processing queue
- Currently processing tasks are marked for cancellation and stop at the next checkpoint
- Resources are cleaned up promptly
- Users receive immediate feedback through the web interface

## Memory Optimization

Recent improvements include memory-efficient video composition to prevent hanging when AI avatars are enabled:

- **Per-slide processing**: Videos are processed one slide at a time to prevent memory exhaustion
- **Video validation**: Avatar videos are validated before processing to catch corruption issues
- **Resource cleanup**: Proper cleanup of video clips and garbage collection after each slide
- **Optimized encoding**: Reduced memory usage with optimized video encoding settings
- **30-minute timeout**: Protection against hanging processes with automatic timeout

## Video Composition Improvements

- **Batch processing**: Process slides individually to manage memory
- **Error handling**: Graceful handling of corrupted avatar videos
- **Progress logging**: Real-time feedback during video composition
- **Memory-safe scaling**: Automatic dimension adjustment based on available memory