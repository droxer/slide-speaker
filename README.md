# SlideSpeaker

From slides to videos with AI voices and avatars.

## Key Features

- **Unified Storage System**: Support for Local filesystem, AWS S3, and Aliyun OSS with automatic fallback
- **Memory-Efficient Video Processing**: Optimized video composition to prevent hanging with AI avatars
- **Distributed Processing**: Background task processing with Redis queue for scalability
- **Real-time Progress Tracking**: Live updates on video generation progress
- **Instant Task Cancellation**: Immediate cancellation of processing tasks with resource cleanup
- **Multi-language Support**: Generate content in English, Chinese, Japanese, Korean, and Thai
- **Multiple AI Services**: OpenAI and Qwen for script generation, HeyGen and DALL-E for avatars
- **Flexible TTS Options**: OpenAI TTS, ElevenLabs, and local TTS providers
- **Transcript Revision**: AI-powered transcript refinement for better presentation flow
- **Subtitle Generation**: Automatic subtitle creation in multiple languages with locale-aware filenames
- **Responsive Web Interface**: Modern React frontend with real-time feedback
- **Video Validation**: Automatic validation of avatar videos before processing
- **State Persistence**: Local storage prevents data loss on page refresh
- **Enhanced UI**: Improved user experience with better error handling
- **Task Monitoring**: Comprehensive task tracking and management with statistics
- **Task-based Downloads**: Stable, task-id-based endpoints for video, audio, transcripts, and subtitles
- **Consistent Subtitles**: Subtitle generation respects `subtitle_language` and styling is consistent in preview and completed views
- **Refined Task Monitor**: Clean task cards with link-style “More” toggle exposing all downloads (Video, Audio, Transcript, VTT, SRT)
- **Theme Support**: Ultra‑Flat and Subtle‑Material themes with aligned status pills and interactions
- **Typography**: Google Open Sans as the default font across the web app
- **Watermark Integration**: Automatic watermarking of generated videos
- **Advanced PDF Processing**: Specialized handling for PDF files with chapter-based analysis and AI-generated content

## Quick Start

1. **API Setup**
   ```bash
   cd api
   uv sync                      # Install base dependencies
   uv sync --extra=dev          # Install with development tools (ruff, mypy, pre-commit)
   uv sync --extra=aws          # Install with AWS S3 support (boto3)
   uv sync --extra=oss          # Install with Aliyun OSS support (oss2)
   # Create .env with your API keys and storage configuration
   make dev
   ```

2. **Web Setup**
   ```bash
   cd web
   pnpm install  # or npm install
   pnpm start    # or npm start
   ```

3. **Visit** `http://localhost:3000` to upload presentations and create AI-powered videos

4. **API Documentation** is available at `http://localhost:8000/docs`

5. **Downloads & Endpoints**
   - Frontend and documentation use task-based endpoints:
     - `/api/tasks/{task_id}/video`
     - `/api/tasks/{task_id}/audio`
     - `/api/tasks/{task_id}/transcripts/markdown`
     - `/api/tasks/{task_id}/subtitles/vtt|srt`
   - The backend continues to serve legacy file-based routes for compatibility.

## Documentation

For detailed documentation, see the [docs](docs/) directory:

- [Installation Guide](docs/installation.md)
- [API Documentation](docs/api.md)

## License

This project is licensed under the MIT License.
