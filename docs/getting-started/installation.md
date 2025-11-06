# Backend Installation Guide

## Prerequisites

- Python 3.12+
- Redis server
- FFmpeg (required for media processing)
- API keys for:
  - OpenAI (for transcript generation)
  - ElevenLabs or OpenAI TTS (for audio generation)

## Backend Setup

1. Navigate to the API directory:
   ```bash
   cd api
   ```

2. Install Python dependencies:
   ```bash
   uv sync                      # Install base dependencies
   uv sync --extra=dev          # Install with development tools (ruff, mypy, pre-commit)
   ```

3. Create a `.env` file in the `api/` directory (see also `api/.env.example`):
   ```env
   # AI Service Keys
   OPENAI_API_KEY=your_openai_api_key
   TTS_SERVICE=openai               # Options: openai, elevenlabs
   ELEVENLABS_API_KEY=your_elevenlabs_api_key   # If using ElevenLabs

   # Redis Configuration
   REDIS_HOST=localhost
   REDIS_PORT=6379

   # Storage Configuration (optional - defaults to local filesystem)
   STORAGE_PROVIDER=local  # Options: local, s3, oss
   ```

4. Start Redis:
   ```bash
   # On macOS with Homebrew
   brew services start redis
   ```

5. Start the API server:
   ```bash
   # Development mode
   make api

   # Or start with the master-worker pattern for production:
   # Terminal 1: Start API server
   make start
   # Terminal 2: Start master worker
   make master-worker
   ```

6. Alternatively, start components directly:
   ```bash
   # API server only
   uv run python server.py
   
   # Master worker (in separate terminal)
   uv run python master_worker.py
   ```

## API Documentation

Once running, the API documentation will be available at:
- Interactive docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc