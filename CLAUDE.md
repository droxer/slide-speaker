# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start Commands

### Backend (FastAPI)
```bash
cd api
uv sync                      # Install base dependencies
uv sync --extra=dev          # Install with development tools (ruff, mypy, pre-commit)
uv sync --extra=aws          # Install with AWS S3 support (boto3)
uv sync --extra=oss          # Install with Aliyun OSS support (oss2)
uv sync --extra=dev --extra=aws --extra=oss  # Install all optional dependencies
python server.py             # Start API server (port 8000)
python master_worker.py      # Start master worker for background tasks
python cli.py --help         # Show CLI tool help
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
- **Services**: OpenAI/Qwen (transcripts), ElevenLabs/OpenAI TTS (audio), HeyGen/DALL-E (avatars), FFmpeg (video composition)

### Processing Pipeline
1. **Upload**: PDF/PPTX → `uploads/` directory
2. **Extraction**: PDF/PPTX → slide images + text content
3. **Transcript Generation**: OpenAI/Qwen creates presentation transcripts per slide
4. **Transcript Revision**: AI revises transcripts for better flow
5. **Audio Generation**: Text-to-speech with ElevenLabs, OpenAI, or local TTS
6. **Avatar Generation**: HeyGen/DALL-E creates AI presenter videos (optional)
7. **Video Composition**: FFmpeg combines slides + avatar + audio into final MP4
8. **Output**: `output/{file_id}_final.mp4` with optional subtitles

### Key Components

**Backend Services**:
- `api/slidespeaker/core/` - State management, task queue, pipeline coordination
- `api/slidespeaker/processing/` - Video composition, subtitle generation, image processing
- `api/slidespeaker/services/` - External API integrations (OpenAI, Qwen, ElevenLabs, HeyGen, DALL-E)
- `api/slidespeaker/pipeline/` - Individual processing steps (extract slides, generate transcripts, etc.)

**State Management**:
- Redis-based task queue with cancellation support
- File-based state persistence for long-running tasks
- Real-time progress tracking via WebSocket updates

**Storage Architecture**:
- Extensible cloud storage system with abstract `StorageProvider` interface
- Support for multiple providers: Local filesystem, AWS S3, Aliyun OSS
- Automatic fallback to local storage if cloud upload fails
- Presigned URL generation for secure file access
- All pipeline steps automatically upload to configured storage provider
- Unified URL generation across all storage providers
- Locale-aware subtitle filename generation with backward compatibility

**File Structure**:
- `api/` - FastAPI backend
- `web/` - React frontend
- `uploads/` - Temporary uploaded files
- `output/` - Generated videos and subtitles (local storage)
- `.env` - API keys (OpenAI, Qwen, ElevenLabs, HeyGen) and storage configuration

### Environment Setup
Required API keys in `api/.env`:
```
OPENAI_API_KEY=your_key
QWEN_API_KEY=your_key
ELEVENLABS_API_KEY=your_key
HEYGEN_API_KEY=your_key

# Storage Configuration (optional - defaults to local filesystem)
STORAGE_PROVIDER=local  # Options: local, s3, oss

# AWS S3 Configuration (required when STORAGE_PROVIDER=s3)
AWS_S3_BUCKET_NAME=your-bucket-name
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key

# Aliyun OSS Configuration (required when STORAGE_PROVIDER=oss)
OSS_BUCKET_NAME=your-bucket-name
OSS_ENDPOINT=oss-cn-region.aliyuncs.com
OSS_ACCESS_KEY_ID=your-access-key-id
OSS_ACCESS_KEY_SECRET=your-access-key-secret
OSS_REGION=cn-region
```

### Development Workflow
1. Start backend: `cd api && python server.py`
2. Start frontend: `cd web && pnpm start`
3. Access UI at http://localhost:3000
4. API docs at http://localhost:8000/docs

### Recent Improvements
**Storage System Overhaul**:
- Replaced Google Cloud Storage with Aliyun OSS support
- Added comprehensive Aliyun OSS implementation with presigned URLs
- Unified storage provider interface across local, S3, and OSS
- Fixed URL generation for consistent behavior across all storage providers
- Added locale-aware subtitle filename generation (e.g., `_en.srt`, `_zh-Hans.vtt`)
- Maintains backward compatibility with legacy filename formats

**Memory-Optimized Video Processing**:
- Per-slide processing to prevent memory exhaustion
- Video validation before processing
- Proper resource cleanup and garbage collection
- 30-minute timeout protection

**Enhanced User Experience**:
- Local storage for task state persistence (prevents data loss on page refresh)
- Smoother subtitle transitions between slides
- Improved UI with better error handling and progress tracking
- Fixed video preview modal darkness issues with optimized overlay styling

**Code Quality Improvements**:
- Fixed E402 import order errors in transcript_reviewer.py by moving imports to the top of the file
- Consolidated documentation into single CLAUDE.md file (removed separate docs/ directory)
- Added more descriptive comments throughout codebase
- Improved logging configuration for better debugging
- Updated Redis key namespace from "ai_slider" to "ss" for consistency
- do NOT git commit
- do NOT check the node_modules and .venv
