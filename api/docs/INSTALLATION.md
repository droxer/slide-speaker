# SlideSpeaker API Installation Guide

## Prerequisites

- Python 3.12+
- Redis server
- FFmpeg
- API keys for:
  - OpenAI (for transcript generation, translation, and image generation)
  - ElevenLabs or OpenAI TTS (for audio generation)
  - HeyGen (for avatar generation)

## Backend Setup

1. Navigate to the API directory:
   ```bash
   cd api
   ```

2. Install Python dependencies:
   ```bash
   uv sync                      # Install base dependencies
   uv sync --extra=dev          # Install with development tools (ruff, mypy, pre-commit)
   uv sync --extra=aws          # Install with AWS S3 support (boto3)
   uv sync --extra=oss          # Install with Aliyun OSS support (oss2)
   uv sync --extra=dev --extra=aws --extra=oss  # Install all optional dependencies
   ```

3. Create a `.env` file in the `api/` directory (see also `api/.env.example`):
   ```env
   # AI Service Keys (at least one from each category)
   OPENAI_API_KEY=your_openai_api_key
   OPENAI_BASE_URL=                  # Optional: set for OpenAI-compatible endpoints
   OPENAI_TIMEOUT=60                 # Default request timeout (seconds)
   OPENAI_RETRIES=3                  # Retry attempts for LLM/image/tts calls
   OPENAI_BACKOFF=0.5                # Initial backoff seconds (exponential)
   LLM_PROVIDER=openai               # LLM provider (openai; google in future)
   # Qwen has been removed; no QWEN_API_KEY required

   ELEVENLABS_API_KEY=your_elevenlabs_api_key

   HEYGEN_API_KEY=your_heygen_api_key

   # Redis Configuration
   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_PASSWORD=your_redis_password_or_empty

   # Storage Configuration (optional - defaults to local filesystem)
   STORAGE_PROVIDER=local  # Options: local, s3, oss

   # AWS S3 Configuration (required when STORAGE_PROVIDER=s3)
   AWS_S3_BUCKET_NAME=your-bucket-name
   AWS_REGION=us-east-1
   AWS_ACCESS_KEY_ID=your-access-key-id
   AWS_SECRET_ACCESS_KEY=your-secret-access-key
   # Optional: For S3-compatible endpoints (e.g., MinIO)
   AWS_S3_ENDPOINT_URL=

   # Aliyun OSS Configuration (required when STORAGE_PROVIDER=oss)
   OSS_BUCKET_NAME=your-bucket-name
   OSS_ENDPOINT=oss-cn-region.aliyuncs.com
   OSS_ACCESS_KEY_ID=your-access-key-id
   OSS_ACCESS_KEY_SECRET=your-access-key-secret
   OSS_REGION=cn-region
   # Set to true if you use a custom CNAME domain for your bucket
   OSS_IS_CNAME=false

   # Media proxy: set true to stream cloud media through API and bypass bucket CORS
   PROXY_CLOUD_MEDIA=false

   # Provider selection (LLM/translation/tts)
   SCRIPT_PROVIDER=openai           # Options: openai
   OPENAI_SCRIPT_MODEL=gpt-4o
   TRANSLATION_PROVIDER=openai       # Options: openai
   OPENAI_TRANSLATION_MODEL=gpt-4o-mini
   # Qwen removed: no QWEN_* models
   IMAGE_PROVIDER=openai
   OPENAI_IMAGE_MODEL=gpt-image-1

   # TTS Configuration
   TTS_SERVICE=openai               # Options: openai, elevenlabs
   OPENAI_TTS_MODEL=tts-1
   OPENAI_TTS_VOICE=alloy
   ELEVENLABS_VOICE_ID=

   # Reviewer and vision providers (override independently)
   REVIEW_PROVIDER=openai
   OPENAI_REVIEW_MODEL=gpt-4o
   VISION_PROVIDER=openai
   OPENAI_VISION_MODEL=gpt-4o-mini
   # PDF analyzer
   PDF_ANALYZER_PROVIDER=openai
   OPENAI_PDF_ANALYZER_MODEL=gpt-4o-mini
   # QWEN_PDF_ANALYZER_MODEL removed

   # Watermark Configuration
   WATERMARK_ENABLED=true           # Enable/disable watermark (default: true)
   WATERMARK_TEXT="SlideSpeaker AI" # Watermark text (default: "SlideSpeaker AI")
   WATERMARK_OPACITY=0.95           # Watermark opacity 0.0-1.0 (default: 0.95)
   WATERMARK_SIZE=64                # Watermark font size in pixels (default: 64)
   ```

4. Start Redis:
   ```bash
   # On macOS with Homebrew
   brew services start redis

   # Or using the provided Makefile
   make redis-start
   ```

5. Start the API server and background workers:
   ```bash
   # Development mode (API server with embedded worker)
   make dev

   # Production mode (distributed architecture - recommended)
   # Terminal 1:
   make start
   # Terminal 2:
   make master-worker

   # Alternative: Standalone worker mode (for simpler deployments)
   # Terminal 1:
   STANDALONE_WORKER=true make start
   # Terminal 2:
   make worker
   ```

6. Alternatively, start components directly:
   ```bash
   # API server only (with embedded worker)
   uv run python server.py

   # Master worker (in separate terminal - recommended for production)
   uv run python master_worker.py

   # Standalone worker (in separate terminal - alternative approach)
   STANDALONE_WORKER=true uv run python worker.py
   ```

## Unified Storage System

SlideSpeaker features a unified storage system that supports multiple storage providers:

- **Local Filesystem**: Default option, stores files in the `output/` directory
- **AWS S3**: Cloud storage option for scalable hosting
- **Aliyun OSS**: Alternative cloud storage option, particularly useful in China

### Storage Provider Configuration

The `STORAGE_PROVIDER` environment variable determines which storage system to use:
- `local`: Files are stored in the local filesystem under the `output/` directory
- `s3`: Files are stored in AWS S3 (requires AWS configuration)
- `oss`: Files are stored in Aliyun OSS (requires OSS configuration)

### Automatic Fallback

If cloud storage upload fails, the system automatically falls back to local storage to ensure file availability.

### Presigned URLs

All storage providers support presigned URL generation for secure file access, allowing users to download files without exposing credentials.

If you deploy behind strict bucket CORS or a restrictive CDN, you can set `PROXY_CLOUD_MEDIA=true` to proxy media (video/audio) through the API origin. This avoids CORS issues at the cost of server bandwidth.

### Locale-aware Subtitle Filenames

The system generates locale-aware subtitle filenames (e.g., `_en.srt`, `_zh-Hans.vtt`) and prefers task-id-based names when a task ID is available (e.g., `{task_id}_{locale}.vtt|srt`). Legacy file-based names remain readable for backward compatibility.

## Watermark Integration

All generated videos automatically include a watermark for branding and protection:

- **Configurable watermark text**: Customize the watermark text via environment variables
- **Adjustable opacity**: Control watermark visibility (default: 0.95)
- **Customizable size**: Adjust watermark size to fit your needs (default: 64)
- **Highly visible positioning**: Watermark is positioned in the bottom-right corner for maximum visibility

### Watermark Configuration

Configure the watermark via environment variables in your `.env` file:

```env
WATERMARK_ENABLED=true           # Enable/disable watermark (default: true)
WATERMARK_TEXT="SlideSpeaker AI" # Watermark text (default: "SlideSpeaker AI")
WATERMARK_OPACITY=0.95           # Watermark opacity 0.0-1.0 (default: 0.95)
WATERMARK_SIZE=64                # Watermark font size in pixels (default: 64)
```

## Task Cancellation

SlideSpeaker features improved task cancellation that allows users to immediately stop processing tasks. When a task is cancelled:

- Queued tasks are removed from the processing queue
- Currently processing tasks are marked for cancellation and stop at the next checkpoint
- Resources are cleaned up promptly
- Users receive immediate feedback through the web interface

### Enhanced Cancellation Capabilities

Recent improvements include:
- **Immediate feedback**: Users receive real-time updates when tasks are cancelled
- **Resource cleanup**: System automatically cleans up temporary files and resources
- **Graceful termination**: Processing tasks stop at the next safe checkpoint
- **State preservation**: Task state is preserved for review even after cancellation

## Task Monitoring

SlideSpeaker includes comprehensive task monitoring capabilities that allow users and administrators to track, search, and analyze processing tasks:

- **Task listing**: View all tasks with filtering and pagination options
- **Task search**: Search for specific tasks by file ID or properties
- **Detailed statistics**: Get comprehensive statistics on task processing
- **Individual task details**: View detailed information about specific tasks
- **Task cancellation**: Cancel specific tasks through API endpoints

### Monitoring Features

Recent enhancements include:
- **Real-time statistics**: View success rates, processing times, and recent activity
- **Advanced filtering**: Filter tasks by status, creation date, and other properties
- **Detailed analytics**: Understand language usage, success/failure rates, and processing patterns
- **Comprehensive search**: Find tasks quickly using search queries
- **Unified downloads**: Task cards show a link-style "More" toggle revealing task-based downloads in this order: Video, Audio, Transcript, VTT, SRT
- **Consistent subtitles**: Subtitle styling is aligned between preview and completed views and uses the requested `subtitle_language`
- **Theme support**: Ultra-Flat and Subtle-Material themes with status pill colors and accessible focus states
- **Typography**: Google Open Sans as the default font for consistent UI

## Memory Optimization

Recent improvements include memory-efficient video composition to prevent hanging when AI avatars are enabled:

- **Per-slide processing**: Videos are processed one slide at a time to prevent memory exhaustion
- **Video validation**: Avatar videos are validated before processing to catch corruption issues
- **Resource cleanup**: Proper cleanup of video clips and garbage collection after each slide
- **Optimized encoding**: Reduced memory usage with optimized video encoding settings
- **30-minute timeout**: Protection against hanging processes with automatic timeout

## Video Composition Improvements

- **Batch processing**: Process slides individually to manage memory
- **Error handling**: Graceful handling of corrupted avatar videos
- **Progress logging**: Real-time feedback during video composition
- **Memory-safe scaling**: Automatic dimension adjustment based on available memory
- **Watermark integration**: Automatic addition of watermarks to final videos

## Service Configuration Options

### AI Service Selection

The application supports multiple AI service providers. You can configure which services to use:

#### Transcript Generation
- Provider: `SCRIPT_PROVIDER=openai`
- OpenAI: Set `OPENAI_API_KEY` and `OPENAI_SCRIPT_MODEL`

#### Text-to-Speech
- Provider: `TTS_SERVICE=openai|elevenlabs`
- OpenAI TTS: Uses `OPENAI_API_KEY`, `OPENAI_TTS_MODEL`, `OPENAI_TTS_VOICE`
- ElevenLabs: Set `ELEVENLABS_API_KEY` and optional `ELEVENLABS_VOICE_ID`

#### Review and Revision
- Provider: `REVIEW_PROVIDER=openai`
- OpenAI: Set `OPENAI_API_KEY`, `OPENAI_REVIEW_MODEL`

#### Vision Analysis
- Provider: `VISION_PROVIDER=openai`
- OpenAI: Set `OPENAI_API_KEY`, `OPENAI_VISION_MODEL`

#### PDF Analysis
- Provider: `PDF_ANALYZER_PROVIDER=openai`
- OpenAI: Set `OPENAI_API_KEY`, `OPENAI_PDF_ANALYZER_MODEL`

#### Image Generation
- HeyGen: Set `HEYGEN_API_KEY` for realistic AI presenters
- OpenAI Images: Uses `OPENAI_API_KEY` with `OPENAI_IMAGE_MODEL`; set `IMAGE_PROVIDER=openai`

#### Translation
- Provider: `TRANSLATION_PROVIDER=openai`
- OpenAI: Set `OPENAI_API_KEY`, `OPENAI_TRANSLATION_MODEL`

### TTS and LLM Catalog Endpoints
- List TTS voices: `GET /api/tts/voices?language=english[&provider=openai|elevenlabs]`
- TTS catalog: `GET /api/tts/catalog[?provider=...]`
- LLM models: `GET /api/llm/models`

These help the UI populate voice pickers and display active providers/models.