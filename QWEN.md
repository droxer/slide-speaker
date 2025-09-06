# SlideSpeaker Project Context

## Project Overview

SlideSpeaker is an AI-powered application that transforms PDF and PowerPoint presentations into engaging video presentations with AI-generated narration and avatars. The application uses a distributed microservices architecture with clear separation of concerns.

### Key Features
- Memory-Efficient Video Processing: Optimized video composition to prevent hanging with AI avatars
- Distributed processing with Redis queue for scalability
- Real-time progress tracking
- Instant task cancellation with resource cleanup
- Multi-language support (English, Chinese, Japanese, Korean, Thai)
- AI avatar integration (HeyGen and DALL-E)
- Text-to-speech (OpenAI, Qwen, and ElevenLabs)
- AI-powered script refinement for better presentation flow
- Automatic subtitle generation
- Responsive React frontend
- Video validation: Automatic validation of avatar videos before processing
- State persistence: Local storage prevents data loss on page refresh
- Enhanced UI: Improved user experience with better error handling
- Task monitoring: Comprehensive task tracking and management with statistics
- Watermark integration: Automatic watermarking of generated videos

### Architecture
```
┌─────────────────┐    HTTP Requests    ┌──────────────────┐
│   Web Client    │ ──────────────────▶ │   API Server     │
│  (React App)    │                     │  (server.py)     │
└─────────────────┘                     └──────────────────┘
                                                 │
                                                 ▼
                                       ┌──────────────────┐
                                       │  Task Queue      │
                                       │   (Redis)        │
                                       └──────────────────┘
                                                 │
                                                 ▼
                             ┌─────────────────────────────────┐
                             │     Master Worker               │
                             │   (master_worker.py)            │
                             └─────────────────────────────────┘
                                                 │
                   ┌─────────────────┬─────────────┬─────────────────┐
                   ▼                 ▼             ▼                 ▼
         ┌──────────────────┐ ┌──────────────────┐ ...    ┌──────────────────┐
         │  Task Worker 1   │ │  Task Worker 2   │        │  Task Worker N   │
         │ (worker.py)      │ │ (worker.py)      │        │ (worker.py)      │
         └──────────────────┘ ┌──────────────────┘        └──────────────────┘
                   │          │                                     │
                   ▼          ▼                                     ▼
         ┌──────────────────┐┌──────────────────┐        ┌──────────────────┐
         │  External APIs   ││  External APIs   │        │  External APIs   │
         │ (OpenAI,Qwen,    ││ (OpenAI,Qwen,    │        │ (OpenAI,Qwen,    │
         │  ElevenLabs,     ││  ElevenLabs,     │        │  ElevenLabs,     │
         │  HeyGen,DALL-E)  ││  HeyGen,DALL-E)  │        │  HeyGen,DALL-E)  │
         └──────────────────┘└──────────────────┘        └──────────────────┘
```

### Component Descriptions
- **API Server** (`server.py`): Handles all HTTP requests, user interactions, and task queuing
- **Master Worker** (`master_worker.py`): Polls Redis for tasks and dispatches to worker processes
- **Task Workers** (`worker.py`): Process individual video generation tasks in isolation

## Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality and consistency. The hooks run:
- API linting, formatting, and type checking
- Web linting, formatting, and type checking

To set up pre-commit hooks:
```bash
# Run the setup script
./setup-precommit.sh

# Or manually install
cd api
uv run pre-commit install
```

To run pre-commit checks manually:
```bash
# In the api directory
pre-commit run --all-files
```

## Setup and Installation

### Prerequisites
- Python 3.12+
- Node.js 20+
- Redis server
- FFmpeg
- API keys for OpenAI, Qwen, ElevenLabs, and HeyGen

### Backend Setup
```bash
# Navigate to API directory
cd api

# Install dependencies
uv sync

# Create .env file with API keys
# OPENAI_API_KEY=your_openai_api_key
# QWEN_API_KEY=your_qwen_api_key
# ELEVENLABS_API_KEY=your_elevenlabs_api_key
# HEYGEN_API_KEY=your_heygen_api_key
# REDIS_HOST=localhost
# REDIS_PORT=6379
# REDIS_PASSWORD=your_redis_password_or_empty

# Start Redis
brew services start redis

# Start API server and workers (production mode - recommended)
# Terminal 1:
make start
# Terminal 2:
make master-worker
```

### Frontend Setup
```bash
# Navigate to web directory
cd web

# Install dependencies
pnpm install

# Start development server
pnpm start
```

The frontend will be available at `http://localhost:3000` and automatically proxy API requests to the backend at `http://localhost:8000`.

## Key Commands

### Backend Commands
```bash
# Development server with auto-reload
make dev

# Production server
make start

# Master worker (manages multiple worker processes)
make master-worker

# Linting
make lint

# Formatting
make format

# Type checking
make typecheck

# Combined check (linting and type checking)
make check

# Clean temporary files
make clean
```

### Frontend Commands
```bash
# Start development server
pnpm start

# Build for production
pnpm run build

# Run tests
pnpm test

# Lint code
pnpm run lint

# Fix linting issues
pnpm run lint:fix

# Type checking
pnpm run typecheck

# Combined check
pnpm run check
```

## API Documentation

### Base URL
All API endpoints are relative to: `http://localhost:8000/api`

### Key Endpoints
- `POST /api/upload` - Upload a presentation for processing
- `GET /api/progress/{file_id}` - Get processing progress
- `GET /api/video/{file_id}` - Download completed video
- `GET /api/subtitles/{file_id}/srt` - Download SRT subtitles
- `GET /api/subtitles/{file_id}/vtt` - Download VTT subtitles
- `GET /api/task/{task_id}` - Get task status
- `POST /api/task/{task_id}/cancel` - Cancel task processing
- `GET /api/languages` - Get supported languages
- `GET /api/tasks` - Get list of all tasks with filtering and pagination
- `GET /api/tasks/search` - Search for tasks by file ID or properties
- `GET /api/tasks/statistics` - Get comprehensive task statistics
- `GET /api/tasks/{task_id}` - Get detailed information about a specific task
- `DELETE /api/tasks/{task_id}` - Cancel a specific task

### Processing Steps
1. extract_slides - Extract content from the presentation file
2. convert_slides_to_images - Convert slides to image format
3. analyze_slide_images - Analyze visual content using AI
4. generate_scripts - Generate AI narratives for each slide
5. review_scripts - Review and refine scripts for consistency
6. generate_audio - Create text-to-speech audio files
7. generate_avatar_videos - Generate AI avatar videos
8. compose_video - Compose final video presentation

## Development Workflow

### Backend Development
1. Make changes to Python files in the `api/` directory
2. Use `make dev` for development with auto-reload
3. Run `make check` to lint and type-check code
4. Run `make format` to format code with ruff

### Frontend Development
1. Make changes to files in the `web/src/` directory
2. Use `pnpm start` for development with hot reload
3. Run `pnpm run check` to lint and type-check code
4. Run `pnpm run lint:fix` to automatically fix linting issues

### Code Quality Checks
The project uses pre-commit hooks to ensure code quality. These hooks automatically run:
- API linting (`make lint` in api directory)
- API formatting (`make format` in api directory)
- API type checking (`make typecheck` in api directory)
- Web linting (`pnpm run lint` in web directory)
- Web formatting (`pnpm run lint:fix` in web directory)
- Web type checking (`pnpm run typecheck` in web directory)

Before committing, you can manually run all checks with:
```bash
cd api && pre-commit run --all-files
```

## Task Cancellation

SlideSpeaker features improved task cancellation that allows users to immediately stop processing tasks:
- Queued tasks are removed from the processing queue
- Currently processing tasks are marked for cancellation and stop at the next checkpoint
- Resources are cleaned up promptly
- Users receive immediate feedback through the web interface

## Task Monitoring

SlideSpeaker now includes comprehensive task monitoring capabilities:
- List all tasks with filtering and pagination
- Search for specific tasks by file ID or properties
- Get detailed statistics about task processing
- View detailed information about individual tasks
- Cancel specific tasks through the API

## Watermark Integration

All generated videos automatically include a watermark:
- Configurable watermark text (default: "SlideSpeaker AI")
- Adjustable opacity (default: 0.95)
- Customizable size (default: 64)
- Highly visible positioning in the bottom-right corner

Configuration via environment variables:
```
WATERMARK_ENABLED=true
WATERMARK_TEXT="SlideSpeaker AI"
WATERMARK_OPACITY=0.95
WATERMARK_SIZE=64
```

## Troubleshooting Redis Issues

If you encounter issues with task processing, check the following:

1. **Redis Database Configuration**: Ensure that the REDIS_DB environment variable in your `.env` file matches the database where tasks are stored. Mismatched configurations can cause workers to fail to find tasks.

2. **Stale Tasks**: Clean up stale tasks from Redis databases that are no longer in use:
   ```bash
   # Check for tasks in different Redis databases
   redis-cli -n 0 keys "ss:*"
   redis-cli -n 7 keys "ss:*"
   
   # Remove stale tasks from unused databases
   redis-cli -n 0 del ss:task:TASK_ID
   ```

3. **Processing Queue Cleanup**: If tasks are stuck in the processing queue:
   ```bash
   # Check the processing queue
   redis-cli llen ss:task_queue:processing
   
   # Remove tasks from processing queue
   redis-cli lrem ss:task_queue:processing 1 TASK_ID
   ```

## Common Syntax Errors

### Script Reviewer Syntax Error
If you encounter a syntax error in `slidespeaker/processing/script_reviewer.py`:
```
SyntaxError: '{' was never closed
```

This is typically caused by malformed dictionary syntax in the `INSTRUCTION_PROMPTS` dictionary. To fix:
1. Ensure all dictionary entries are separated by commas
2. Verify that all multi-line strings are properly formatted
3. Check that the dictionary has a closing brace `}`

See `docs/script-reviewer-fix.md` for detailed information about this specific issue.

## Development Priorities

Based on the current TODO.md file, the project's logging improvements are a key focus area:

### New Features
- [x] Add structured logging with key-value pairs for better searchability
- [x] Implement log levels configuration via environment variables
- [ ] Add trace-level logging for detailed debugging
- [x] Implement log rotation and retention policies
- [ ] Add JSON logging format option for better parsing

### Enhancement
- [x] Add more warning logs in master worker for worker process issues
- [x] Enhance debug logging in task queue operations
- [x] Add warning logs for Redis connection issues and timeouts
- [x] Improve error logging with more contextual information
- [x] Add performance logging for long-running operations
- [x] Implement consistent log message formatting across all modules
- [ ] Add resource usage logging (memory, CPU) for monitoring
- [x] Enhance cancellation logging with more detailed information
- [ ] Add logging for retry attempts and backoff strategies
- [x] Implement log filtering by component or task ID

### Integration
- [ ] Integrate with Sentry for error tracking and monitoring
- [ ] Add Datadog integration for application performance monitoring
- [ ] Integrate with ELK stack for centralized log management
- [ ] Add Prometheus integration for metrics collection
- [ ] Integrate with Grafana for dashboard visualization
- [ ] Add Loggly integration for log management
- [ ] Integrate with CloudWatch for AWS deployments
- [ ] Add Google Cloud Logging integration
- [ ] Integrate with Azure Monitor for Microsoft cloud deployments
- [ ] Add webhook integration for custom log forwarding

## Logging Improvements

The project now includes enhanced logging capabilities:

### Features
- Structured logging with consistent formatting
- Configurable log levels via environment variables
- File-based logging with rotation and retention policies
- Enhanced warning and error logging with contextual information
- Performance logging for long-running operations
- Thread-safe logging for async environments

### Configuration
- `LOG_LEVEL` - Set log level (DEBUG, INFO, WARNING, ERROR)
- `LOG_FILE` - Optional file path for file-based logging

### Benefits
- Better debugging with detailed debug information
- Improved monitoring with progress tracking
- Enhanced error handling with informative error messages
- Production-ready logging with file rotation and compression

## Directory Structure
```
slide-speaker/
├── api/                 # Backend API server and workers
│   ├── server.py        # Main FastAPI server
│   ├── master_worker.py # Master worker process
│   ├── worker.py        # Individual worker processes
│   ├── pyproject.toml   # Python dependencies
│   ├── Makefile         # Build and run commands
│   └── .env.example     # Example environment variables
├── web/                 # Frontend React application
│   ├── package.json     # Node.js dependencies and scripts
│   └── src/             # Source code
├── docs/                # Documentation
│   ├── pipeline-diagrams.md # Pipeline flow diagrams
│   ├── architecture.md      # System architecture
│   ├── api.md              # API documentation
│   └── installation.md     # Setup instructions
└── README.md            # Project overview
```