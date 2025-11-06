# SlideSpeaker API - Project Context

## Project Overview

SlideSpeaker is a FastAPI-based backend service that turns slides/PDFs into narrated videos with features such as transcripts, text-to-speech (TTS), subtitles, and optional AI avatars. The system provides a task orchestration pipeline that handles transcription, TTS jobs, and serves generated media back to clients.

The API follows a distributed architecture with:
- A main FastAPI server (`server.py`) handling HTTP requests and API endpoints
- Worker processes (`worker.py`) handling background processing tasks
- A master worker (`master_worker.py`) that manages worker processes
- Redis-based task queues for job coordination
- Support for multiple storage backends (local, AWS S3, Aliyun OSS)
- Database support with SQLAlchemy and Alembic migrations

## Key Technologies

- **Framework**: FastAPI for the web API
- **Task Queue**: Redis for job coordination
- **Database**: SQLAlchemy with asyncpg for PostgreSQL (optional)
- **Storage**: Local filesystem, AWS S3, or Aliyun OSS for file storage
- **AI Services**: OpenAI, ElevenLabs, Google Gemini for LLM and TTS
- **Media Processing**: MoviePy, FFmpeg for video generation
- **Authentication**: OAuth2 with JWT tokens
- **Packaging**: uv for dependency management

## Project Structure

```
api/
├── server.py              # Main FastAPI application entry point
├── worker.py              # Background worker process for task processing
├── cli.py                 # Command-line interface for task management
├── master_worker.py       # Master process that spawns and manages workers
├── slidespeaker/          # Main application package
│   ├── configs/           # Configuration and logging setup
│   ├── core/              # Core components (state management, task queue)
│   ├── pipeline/          # Processing pipeline implementation
│   ├── routes/            # API route definitions
│   ├── storage/           # Storage provider implementations
│   └── ...                # Other modules (auth, audio, video, etc.)
├── pyproject.toml         # Project dependencies and configuration
├── alembic.ini            # Database migration configuration
├── Makefile               # Build and deployment commands
├── .env.example           # Environment variable template
└── README.md              # Project documentation
```

## Building and Running

### Prerequisites
- Python 3.12+
- Redis server
- PostgreSQL (optional, for database features)
- API keys for OpenAI, ElevenLabs, or other AI services

### Setup Commands

1. **Install dependencies**:
   ```bash
   make install_dev    # Install all dependencies with optional extras
   # or
   uv sync --extra=dev --extra=oss --extra=aws
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

3. **Run the development server**:
   ```bash
   make api            # Start development server with auto-reload (port 8000)
   # or
   uv run python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Run the production server**:
   ```bash
   make start          # Start production server
   ```

5. **Run background workers**:
   ```bash
   make worker         # Start master worker that manages processing tasks
   # or
   python master_worker.py
   ```

6. **Database migrations**:
   ```bash
   make db-upgrade     # Upgrade database to latest schema
   make db-migrate MESSAGE="migration message"  # Create new migration
   ```

7. **Development utilities**:
   ```bash
   make lint           # Run Ruff linter
   make format         # Run Ruff formatter
   make test           # Run unit tests
   make test-cov       # Run tests with coverage
   ```

### API Documentation
- Interactive API docs: `http://localhost:8000/docs`
- ReDoc documentation: `http://localhost:8000/redoc`

## Development Conventions

### Code Style
- Follow Python PEP 8 style guidelines
- Use Ruff for linting and formatting
- Type hints are enforced with mypy
- Use loguru for logging instead of standard logging module

### File Structure
- Route handlers are organized in the `slidespeaker/routes/` directory
- Business logic is in the `slidespeaker/core/` and `slidespeaker/pipeline/` directories
- Configuration is centralized in `slidespeaker/configs/`
- Database models and repositories are in `slidespeaker/repository/`
- Storage implementations are in `slidespeaker/storage/`

### Task Processing
- Tasks are processed asynchronously using Redis as a queue backend
- Each task has a lifecycle: queued → processing → completed/failed/cancelled
- Workers are spawned per task to handle CPU-intensive processing
- Task progress can be monitored via the progress routes

### Environment Configuration
- All configuration should come from environment variables
- The `.env.example` file documents all available configuration options
- Configuration is centralized in `slidespeaker/configs/config.py`
- Different storage providers can be configured (local, S3, OSS)

### Testing
- Tests are located in the `tests/` directory
- Use pytest with asyncio support for async code
- Run tests with `make test` or `pytest tests/ -v`

### CLI Tools
- Task management via `cli.py` for listing, cancelling, and deleting tasks
- User management via scripts/user_cli.py
- Use `make cli` to see available CLI commands

## Key Features

1. **Presentation Processing Pipeline**:
   - PDF and PowerPoint document parsing
   - AI-powered script generation from slides
   - Text-to-speech conversion with multiple voice options
   - Video generation with optional AI avatars
   - Subtitle generation (VTT/SRT formats)
   - Podcast audio generation

2. **Scalable Architecture**:
   - Task-based processing with queue system
   - Distributed worker model
   - Progress tracking for long-running jobs

3. **Authentication & Authorization**:
   - OAuth2 with JWT tokens
   - User management system
   - Protected API endpoints

4. **Storage Options**:
   - Multiple storage backends supported
   - Local file system
   - AWS S3 compatibility
   - Aliyun OSS compatibility

5. **Accessibility**:
   - WCAG 2.1 AA compliance
   - High contrast themes
   - Multi-language support

## Important Configuration

### Essential Environment Variables
- `OPENAI_API_KEY`: Required for transcript generation
- `TTS_SERVICE`: Either "openai" or "elevenlabs" for text-to-speech
- `ELEVENLABS_API_KEY`: Required if using ElevenLabs for TTS
- `REDIS_HOST`, `REDIS_PORT`: Redis connection settings
- `DATABASE_URL`: PostgreSQL connection string (if using database features)
- Storage configuration based on selected provider (local, S3, OSS)

### API Endpoints
- Authentication: `/auth/`
- File upload: `/upload/`
- Task management: `/tasks/`
- Progress tracking: `/progress/`
- Downloads: `/downloads/`, `/video/`, `/audio/`
- Health checks: `/health/`
- User management: `/users/`

This project is under active development with rapid iteration and breaking changes expected until production readiness.