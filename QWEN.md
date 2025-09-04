# SlideSpeaker Project Context

## Project Overview

SlideSpeaker is an AI-powered application that transforms PDF and PowerPoint presentations into engaging video presentations with AI-generated narration and avatars. The application uses a distributed microservices architecture with clear separation of concerns.

### Key Features
- Distributed processing with Redis queue for scalability
- Real-time progress tracking
- Instant task cancellation with resource cleanup
- Multi-language support (English, Chinese, Japanese, Korean, Thai)
- AI avatar integration (HeyGen)
- Text-to-speech (OpenAI and ElevenLabs)
- Automatic subtitle generation
- Responsive React frontend

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
         │ (OpenAI,HeyGen,  ││ (OpenAI,HeyGen,  │        │ (OpenAI,HeyGen,  │
         │  ElevenLabs)     ││  ElevenLabs)     │        │  ElevenLabs)     │
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
- Node.js 16+
- Redis server
- FFmpeg
- API keys for OpenAI, ElevenLabs, and HeyGen

### Backend Setup
```bash
# Navigate to API directory
cd api

# Install dependencies
uv sync

# Create .env file with API keys
# OPENAI_API_KEY=your_openai_api_key
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
npm install

# Start development server
npm start
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
npm start

# Build for production
npm run build

# Run tests
npm test

# Lint code
npm run lint

# Fix linting issues
npm run lint:fix

# Type checking
npm run typecheck

# Combined check
npm run check
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
2. Use `npm start` for development with hot reload
3. Run `npm run check` to lint and type-check code
4. Run `npm run lint:fix` to automatically fix linting issues

### Code Quality Checks
The project uses pre-commit hooks to ensure code quality. These hooks automatically run:
- API linting (`make lint` in api directory)
- API formatting (`make format` in api directory)
- API type checking (`make typecheck` in api directory)
- Web linting (`make lint` in web directory)
- Web formatting (`make lint-fix` in web directory)
- Web type checking (`make typecheck` in web directory)

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

## Troubleshooting Redis Issues

If you encounter issues with task processing, check the following:

1. **Redis Database Configuration**: Ensure that the REDIS_DB environment variable in your `.env` file matches the database where tasks are stored. Mismatched configurations can cause workers to fail to find tasks.

2. **Stale Tasks**: Clean up stale tasks from Redis databases that are no longer in use:
   ```bash
   # Check for tasks in different Redis databases
   redis-cli -n 0 keys "ai_slider:*"
   redis-cli -n 7 keys "ai_slider:*"
   
   # Remove stale tasks from unused databases
   redis-cli -n 0 del ai_slider:task:TASK_ID
   ```

3. **Processing Queue Cleanup**: If tasks are stuck in the processing queue:
   ```bash
   # Check the processing queue
   redis-cli llen ai_slider:task_queue:processing
   
   # Remove tasks from processing queue
   redis-cli lrem ai_slider:task_queue:processing 1 TASK_ID
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

The project has a TODO.md file that outlines development priorities in three categories:

### New Features
- Add support for Keynote (.key) presentation files
- Add support for OpenDocument Presentation (.odp) files
- Implement user authentication and account management system
- Add collaborative editing features for teams
- Create presentation templates and themes
- Add video editing capabilities (trimming, scene cutting)
- Implement analytics dashboard for video performance metrics
- Add voice customization options (pitch, speed, emotion)
- Create mobile app version for on-the-go presentation creation
- Add batch processing for multiple presentations simultaneously

### Enhancement
- Improve drag-and-drop file upload experience with better feedback
- Add real-time preview of avatar selection during creation process
- Create custom avatar selection and configuration interface
- Implement dark mode for the web interface
- Add keyboard shortcuts for common actions and navigation
- Improve progress indicators with more detailed step information
- Optimize image processing pipeline for faster slide conversion
- Add tooltips and contextual help throughout the interface
- Implement responsive design improvements for better mobile experience
- Add video preview functionality before final download

### Integration
- Integrate with Google Drive for file import/export capabilities
- Add Dropbox integration for cloud storage options
- Integrate with Slack for processing notifications and updates
- Add GitHub authentication for user login
- Integrate with Google OAuth for single sign-on
- Add Microsoft Azure AD integration for enterprise users
- Integrate with Stripe for premium feature payments
- Add Sentry integration for error tracking and monitoring
- Integrate with Datadog for application performance monitoring
- Add Zapier integration for workflow automation

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