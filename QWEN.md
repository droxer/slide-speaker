# SlideSpeaker Project Context

## Project Overview

SlideSpeaker is an AI-powered platform that transforms presentations (PowerPoint slides or PDF documents) into engaging video content. The system can automatically generate narrated videos with optional AI avatars, synchronized subtitles, and professional-quality audio.

The project follows a modern microservices architecture with a Python FastAPI backend and a React/TypeScript frontend. It uses Redis for task queuing and state management, and supports multiple AI services (OpenAI, ElevenLabs, HeyGen) for different processing steps.

### Key Features
- Convert PDFs and PowerPoint presentations into narrated videos
- AI-powered script generation and voice synthesis
- Optional AI avatar generation for presentations
- Multi-language support for voice and subtitles
- Cloud storage integration (AWS S3, Aliyun OSS)
- Task monitoring and management
- Real-time progress tracking
- Watermark integration

## Technology Stack

### Backend (API)
- **Language**: Python 3.12+
- **Framework**: FastAPI
- **Task Queue**: Redis
- **Database**: PostgreSQL (optional)
- **AI Services**: 
  - OpenAI (GPT models for script generation, TTS, vision)
  - ElevenLabs (Alternative TTS)
  - HeyGen (AI avatar generation)
- **Media Processing**: FFmpeg, MoviePy
- **Dependency Management**: uv/pip

### Frontend (Web UI)
- **Language**: TypeScript
- **Framework**: React 18
- **Build Tool**: React Scripts
- **State Management**: React Query (TanStack Query)
- **Styling**: Sass/SCSS
- **Package Manager**: pnpm (preferred) or npm

### Infrastructure
- **Containerization**: Docker support
- **Deployment**: Production-ready with master-worker architecture
- **Storage**: Local filesystem, AWS S3, or Aliyun OSS

## Project Structure

```
slide-speaker/
├── api/                 # Backend FastAPI application
│   ├── slidespeaker/    # Core application modules
│   │   ├── configs/     # Configuration and environment management
│   │   ├── core/        # Task queue and state management
│   │   ├── routes/      # API endpoints
│   │   ├── pipeline/    # Processing pipeline coordinators
│   │   ├── processing/  # Media processing components
│   │   ├── services/    # External service integrations
│   │   ├── llm/         # Centralized LLM client helpers
│   │   ├── storage/     # Unified storage interface
│   │   └── repository/  # Database repository layer
│   ├── tests/           # Backend tests
│   ├── uploads/         # Temporary file storage
│   ├── output/          # Generated media output
│   ├── server.py        # Main API server entrypoint
│   ├── worker.py        # Task worker process
│   ├── master_worker.py # Master process for managing workers
│   ├── Makefile         # Development commands
│   ├── pyproject.toml   # Python dependencies
│   └── .env.example     # Environment configuration example
├── web/                 # Frontend React application
│   ├── src/             # Source code
│   │   ├── components/  # React components
│   │   ├── services/    # API client services
│   │   ├── styles/      # SCSS stylesheets
│   │   ├── types/       # TypeScript type definitions
│   │   ├── utils/       # Utility functions
│   │   ├── App.tsx      # Main application component
│   │   └── index.tsx    # Entry point
│   ├── Makefile         # Development commands
│   ├── package.json     # Node.js dependencies
│   └── tsconfig.json    # TypeScript configuration
├── docs/                # Documentation
└── README.md            # Project overview and quick start
```

## Development Environment Setup

### Prerequisites
- Python 3.12+
- Node.js 20+
- Redis server
- FFmpeg
- API keys for:
  - OpenAI (required for transcript generation)
  - ElevenLabs or OpenAI TTS (optional for audio generation)
  - HeyGen or DALL-E (optional for avatar generation)

### Backend Setup
```bash
cd api
uv sync                      # Install base dependencies
cp .env.example .env         # Create config file
# Edit .env to add your API keys
make dev                     # Start development server (port 8000)
```

### Frontend Setup
```bash
cd web
pnpm install                 # Install dependencies (prefer pnpm)
pnpm start                   # Start development server (port 3000)
```

## Key Development Commands

### Backend (API Directory)
- `make install` - Install dependencies via uv
- `make dev` - Start development server with auto-reload
- `make start` - Start production server
- `make master-worker` - Start master process that spawns workers
- `make lint` - Run Ruff linter
- `make format` - Run Ruff formatter
- `make typecheck` - Run mypy type checker
- `make check` - Run both linting and type checking
- `make test` - Run unit tests

### Frontend (Web Directory)
- `make install` - Install dependencies (prefers pnpm)
- `make dev` - Start development server
- `make build` - Build production version
- `make lint` - Run ESLint code linting
- `make typecheck` - Run TypeScript type checking
- `make check` - Run both linting and type checking
- `make test` - Run unit tests

## API Architecture

The backend follows a modular architecture with clear separation of concerns:

1. **Core Layer** (`slidespeaker/core/`)
   - Task queue management using Redis
   - State management for processing tasks
   - Worker coordination

2. **Routes Layer** (`slidespeaker/routes/`)
   - REST API endpoints for all functionality
   - Upload, task management, downloads, health checks

3. **Pipeline Layer** (`slidespeaker/pipeline/`)
   - Processing coordinators for PDF vs slides
   - Task orchestration logic

4. **Processing Layer** (`slidespeaker/processing/`)
   - Audio, video, subtitle, and image processing
   - Media composition and editing

5. **Services Layer** (`slidespeaker/services/`)
   - Integrations with external AI services
   - OpenAI, ElevenLabs, HeyGen clients

6. **LLM Layer** (`slidespeaker/llm/`)
   - Centralized LLM client helpers
   - Chat completion, image generation, TTS functions

7. **Storage Layer** (`slidespeaker/storage/`)
   - Unified interface for different storage providers
   - Local filesystem, AWS S3, Aliyun OSS support

## Frontend Architecture

The frontend is built with React and follows a component-based architecture:

1. **Main Components** (`src/components/`)
   - TaskMonitor: Main dashboard for task monitoring
   - UploadPanel: File upload interface
   - ProcessingView: Real-time processing visualization
   - CompletedView: Final results display
   - Reusable media players (VideoPlayer, AudioPlayer, PodcastPlayer)

2. **Services** (`src/services/`)
   - API client for backend communication
   - React Query hooks for data fetching and caching

3. **State Management**
   - React Query for server state
   - React Context for UI state
   - LocalStorage for task persistence

4. **Styling**
   - SCSS modules for component styling
   - Theme support (Ultra-Flat, Subtle-Material, Classic)
   - Responsive design

## Configuration

### Environment Variables (api/.env)
Key configuration options include:
- `OPENAI_API_KEY` - Required for AI services
- `ELEVENLABS_API_KEY` - Optional for alternative TTS
- `HEYGEN_API_KEY` - Optional for avatar generation
- `REDIS_HOST/PORT` - Redis connection settings
- `STORAGE_PROVIDER` - Storage backend (local, s3, oss)
- `AWS_*` - AWS S3 configuration
- `OSS_*` - Aliyun OSS configuration

See `api/.env.example` for a complete list of configuration options.

## Task Processing Flow

1. **Upload**: User uploads PDF or PowerPoint file
2. **Task Creation**: Backend creates task in Redis queue
3. **Queuing**: Task is added to processing queue
4. **Worker Processing**: Worker processes task through pipeline:
   - File analysis and parsing
   - Script generation using LLM
   - Voice synthesis (TTS)
   - Avatar generation (optional)
   - Video composition
   - Subtitle generation
5. **Storage**: Generated assets stored in configured backend
6. **Completion**: Task marked as completed, results available via API

## Development Guidelines

### Backend (Python)
- Follow 4-space indentation
- Use Ruff for linting (120-character lines)
- Full type annotations required
- Naming conventions:
  - Functions/modules: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`
- Use centralized LLM helpers in `slidespeaker/llm/` instead of direct API calls
- Minimize excessive logging - use `logger.debug` for detailed information and `logger.info` only for important events

### Frontend (TypeScript/React)
- ESLint and TypeScript for code quality
- Components in `src/components/` with PascalCase naming
- SCSS files for styling with matching component names
- Use React Query for data fetching
- Keep functions small and well-typed

### Logging Best Practices

To reduce excessive logging output while maintaining visibility into important events:

1. Use `logger.debug` for detailed information that's useful for troubleshooting but not needed in normal operation
2. Use `logger.info` for important events that indicate progress or significant state changes
3. Use `logger.warning` for recoverable issues that might need attention
4. Use `logger.error` for unrecoverable errors that affect functionality
5. Avoid logging sensitive information like API keys or user data
6. Reduce the frequency of periodic status updates (e.g., from every 5 seconds to every 15-30 seconds)
7. Remove redundant logging statements that provide the same information

### Testing
- Backend: Use pytest for tests in `api/tests/`
- Frontend: Use Jest/React Testing Library in `web/src/**/*.test.tsx`
- Run `make check` in both directories before committing

## Common Development Tasks

### Adding a New API Endpoint
1. Create new route file in `api/slidespeaker/routes/`
2. Add route to `api/server.py`
3. Update frontend services in `web/src/services/` if needed
4. Add React Query hooks in `web/src/services/queries.ts`

### Adding a New Processing Step
1. Add step to appropriate coordinator in `api/slidespeaker/pipeline/`
2. Implement processing logic in `api/slidespeaker/processing/`
3. Update state management in `api/slidespeaker/core/state_manager.py`
4. Add progress tracking in frontend if needed

### Adding a New Storage Provider
1. Implement provider in `api/slidespeaker/storage/`
2. Update configuration handling in `api/slidespeaker/configs/`
3. Add provider selection logic in storage interface

## Useful Entry Points

### Backend
- Main server: `api/server.py`
- Worker process: `api/worker.py`
- Master worker: `api/master_worker.py`
- Task queue: `api/slidespeaker/core/task_queue.py`
- State manager: `api/slidespeaker/core/state_manager.py`

### Frontend
- Main application: `web/src/App.tsx`
- Task monitor: `web/src/components/TaskMonitor.tsx`
- API client: `web/src/services/client.ts`
- React Query hooks: `web/src/services/queries.ts`

## Accessing the Application

Once running, the application is accessible at:
- Web UI: `http://localhost:3000`
- API Documentation: `http://localhost:8000/docs`
- API Base: `http://localhost:8000`

## Deployment Architecture

For production deployments, SlideSpeaker uses a distributed architecture:
- API server handles HTTP requests
- Master worker manages multiple processing workers
- Redis for task queuing and state management
- Cloud storage for media assets
- Reverse proxy (nginx) for serving static assets

This architecture allows for horizontal scaling of processing workers based on demand.