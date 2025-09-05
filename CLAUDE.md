# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start Commands

### Backend (FastAPI)
```bash
cd api
uv sync --extra=dev          # Install dependencies
python server.py             # Start API server (port 8000)
python master_worker.py      # Start master worker for background tasks
make lint                    # Run ruff linter
make format                  # Run ruff formatter  
make typecheck               # Run mypy type checker
make check                   # Run both linting and type checking
```

### Frontend (React)
```bash
cd web
pnpm install                # Install dependencies (preferred)
pnpm start                  # Start dev server (port 3000)
make lint                   # Run ESLint
make typecheck              # Run TypeScript type checking
make check                  # Run both linting and type checking
```

## Architecture Overview

**SlideSpeaker** converts PDF/PPTX presentations into AI-generated videos using:
- **Frontend**: React + TypeScript + Sass (port 3000)
- **Backend**: FastAPI + Redis + Python workers (port 8000)
- **Services**: OpenAI/Qwen (scripts), ElevenLabs/OpenAI TTS (audio), HeyGen/DALL-E (avatars), FFmpeg (video composition)

### Processing Pipeline
1. **Upload**: PDF/PPTX → `uploads/` directory
2. **Extraction**: PDF/PPTX → slide images + text content
3. **Script Generation**: OpenAI/Qwen creates presentation scripts per slide
4. **Script Review**: AI reviews and refines scripts for better flow
5. **Audio Generation**: Text-to-speech with ElevenLabs, OpenAI, or local TTS
6. **Avatar Generation**: HeyGen/DALL-E creates AI presenter videos (optional)
7. **Video Composition**: FFmpeg combines slides + avatar + audio into final MP4
8. **Output**: `output/{file_id}_final.mp4` with optional subtitles

### Key Components

**Backend Services**:
- `api/slidespeaker/core/` - State management, task queue, pipeline coordination
- `api/slidespeaker/processing/` - Video composition, subtitle generation, image processing
- `api/slidespeaker/services/` - External API integrations (OpenAI, Qwen, ElevenLabs, HeyGen, DALL-E)
- `api/slidespeaker/pipeline/` - Individual processing steps (extract slides, generate scripts, etc.)

**State Management**:
- Redis-based task queue with cancellation support
- File-based state persistence for long-running tasks
- Real-time progress tracking via WebSocket updates

**File Structure**:
- `api/` - FastAPI backend
- `web/` - React frontend
- `uploads/` - Temporary uploaded files
- `output/` - Generated videos and subtitles
- `.env` - API keys (OpenAI, Qwen, ElevenLabs, HeyGen)

### Environment Setup
Required API keys in `api/.env`:
```
OPENAI_API_KEY=your_key
QWEN_API_KEY=your_key
ELEVENLABS_API_KEY=your_key
HEYGEN_API_KEY=your_key
```

### Development Workflow
1. Start backend: `cd api && python server.py`
2. Start frontend: `cd web && pnpm start`
3. Access UI at http://localhost:3000
4. API docs at http://localhost:8000/docs

### Recent Improvements
**Memory-Optimized Video Processing**:
- Per-slide processing to prevent memory exhaustion
- Video validation before processing
- Proper resource cleanup and garbage collection
- 30-minute timeout protection

**Enhanced User Experience**:
- Local storage for task state persistence (prevents data loss on page refresh)
- Smoother subtitle transitions between slides
- Improved UI with better error handling and progress tracking

**Code Quality Improvements**:
- Fixed E402 import order errors in script_reviewer.py by moving imports to the top of the file
- Consolidated documentation into single CLAUDE.md file (removed separate docs/ directory)
- Added more descriptive comments throughout codebase
- Improved logging configuration for better debugging
- Updated Redis key namespace from "ai_slider" to "ss" for consistency