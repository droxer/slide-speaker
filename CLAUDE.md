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
- FastAPI server with async processing
- Services architecture in `./api/slidespeaker/`
- File uploads to `uploads/` directory
- Output videos in `output/` directory
- Redis-based state management

## Development Commands

### API Server (Python)
```bash
cd api
uv sync  # Install dependencies
python main.py  # Start server (port 8000)
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

- `slidespeaker/slide_processor.py`: PDF/PPTX content extraction
- `slidespeaker/script_generator.py`: AI script generation with OpenAI
- `slidespeaker/tts_service.py`: Text-to-speech with ElevenLabs/OpenAI
- `slidespeaker/avatar_service.py`: HeyGen avatar video generation  
- `slidespeaker/video_composer.py`: FFmpeg video composition
- `slidespeaker/state_manager.py`: Redis-based processing state tracking
- `slidespeaker/orchestrator.py`: Processing pipeline coordination
- `slidespeaker/task_manager.py`: Background task management

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
- [Development Guide](docs/development.md)
- [API Documentation](docs/api.md)
- [Architecture Overview](docs/architecture.md)
- the generate_script in @api/slidespeaker/script_generator.py not handle traditional chinese and simpified chinese