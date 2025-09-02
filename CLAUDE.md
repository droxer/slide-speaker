# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SlideSpeaker is a full-stack application that converts PDF/PPTX presentations into AI-generated videos using:
- OpenAI for script generation
- HeyGen for AI avatar videos  
- ElevenLabs for text-to-speech
- FFmpeg for video composition

## Architecture

**Frontend (React):** `./web/`
- React app with axios for API calls
- Proxy configured to API server (port 8000)
- Responsive design with App.css

**Backend (FastAPI):** `./api/`
- **API Server** (`server.py`): Handles HTTP requests, task queuing, and status queries
- **Master Worker** (`master_worker.py`): Polls Redis for tasks and dispatches to worker processes
- **Task Workers** (`worker.py`): Process individual video generation tasks in isolation
- Services architecture in `./api/slidespeaker/`
- File uploads to `uploads/` directory
- Output videos in `output/` directory
- Redis-based state management for task coordination

## Development Commands

### API Server (Python)
```bash
cd api
uv sync  # Install dependencies
python server.py  # Start server (port 8000)
```

### Web Client (React)
```bash
cd web
pnpm install    # Install dependencies (preferred)
pnpm start      # Start dev server (port 3000)
# or
npm install
npm start
```

### Environment Setup
```bash
# API keys required in api/.env:
OPENAI_API_KEY=your_key
ELEVENLABS_API_KEY=your_key  
HEYGEN_API_KEY=your_key
```

## Key Services

- `slidespeaker/processing/slide_extractor.py`: PDF/PPTX content extraction
- `slidespeaker/processing/script_generator.py`: AI script generation with OpenAI
- `slidespeaker/services/tts_service.py`: Text-to-speech with ElevenLabs/OpenAI
- `slidespeaker/services/avatar_service_unified.py`: HeyGen avatar video generation  
- `slidespeaker/processing/video_composer.py`: FFmpeg video composition
- `slidespeaker/core/state_manager.py`: Redis-based processing state tracking
- `slidespeaker/core/pipeline.py`: Processing pipeline coordination
- `slidespeaker/core/task_queue.py`: Redis-based task queue management
- `slidespeaker/core/task_manager.py`: Background task management

## Enhanced Task Cancellation

SlideSpeaker now features improved task cancellation with the following enhancements:

1. **Immediate Cancellation Detection**: Tasks can be cancelled quickly through a dedicated Redis key that bypasses normal state checking
2. **Frequent Checkpoints**: Cancellation is checked at regular intervals during long-running operations:
   - Script generation (every 3 slides)
   - Audio generation (every 2 slides)
   - Avatar video generation (every 2 slides)
   - Slide conversion (every 5 slides)
   - Video composition (at key points)
3. **Worker-Level Monitoring**: Task workers check for cancellation every 5 seconds for faster response
4. **Resource Cleanup**: Cancelled tasks properly clean up temporary files and resources

## File Processing Flow

1. Upload PDF/PPTX → `uploads/`
2. Extract slide content → Markdown/text
3. Generate AI scripts per slide → OpenAI
4. Create TTS audio → ElevenLabs/OpenAI  
5. Generate avatar videos → HeyGen
6. Compose final video → FFmpeg
7. Output MP4 → `output/`

## Dependencies

**Python (uv):** FastAPI, OpenAI, ElevenLabs, moviepy, ffmpeg-python, redis
**Node.js (pnpm):** React, axios, testing libraries

## Notes

- Uses Aliyun mirrors for package downloads in China
- FFmpeg required for video processing
- Large files may require increased timeouts
- Background processing handles long-running tasks

## Documentation

Detailed documentation is available in the `docs/` directory:
- [Installation Guide](docs/installation.md)
- [API Documentation](docs/api.md)
- [Architecture Documentation](docs/architecture.md)
- the generate_script in @api/slidespeaker/script_generator.py not handle traditional chinese and simpified chinese