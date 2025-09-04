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
- **Services**: OpenAI (scripts), ElevenLabs/TTS (audio), HeyGen (avatars), FFmpeg (video composition)

### Processing Pipeline
1. **Upload**: PDF/PPTX → `uploads/` directory
2. **Extraction**: PDF/PPTX → slide images + text content
3. **Script Generation**: OpenAI creates presentation scripts per slide
4. **Audio Generation**: Text-to-speech with ElevenLabs or OpenAI
5. **Avatar Generation**: HeyGen creates AI presenter videos (optional)
6. **Video Composition**: FFmpeg combines slides + avatar + audio into final MP4
7. **Output**: `output/{file_id}_final.mp4` with optional subtitles

### Key Components

**Backend Services**:
- `api/slidespeaker/core/` - State management, task queue, pipeline coordination
- `api/slidespeaker/processing/` - Video composition, subtitle generation, image processing
- `api/slidespeaker/services/` - External API integrations (OpenAI, ElevenLabs, HeyGen)
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
- `.env` - API keys (OpenAI, ElevenLabs, HeyGen)

### Environment Setup
Required API keys in `api/.env`:
```
OPENAI_API_KEY=your_key
ELEVENLABS_API_KEY=your_key
HEYGEN_API_KEY=your_key
```

### Development Workflow
1. Start backend: `cd api && python server.py`
2. Start frontend: `cd web && pnpm start`
3. Access UI at http://localhost:3000
4. API docs at http://localhost:8000/docs

### Memory-Optimized Video Processing
Recent improvements include memory-efficient video composition with:
- Per-slide processing to prevent memory exhaustion
- Video validation before processing
- Proper resource cleanup and garbage collection
- 30-minute timeout protection