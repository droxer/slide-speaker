# API Documentation

## Base URL

All API endpoints are relative to: `http://localhost:8000/api`

## Core Endpoints

### Upload Presentation

```
POST /api/upload
```

Upload a PDF or PowerPoint presentation for processing.

**Request:**
- JSON body with base64-encoded file data:
  ```json
  {
    "filename": "presentation.pdf",
    "file_data": "base64-encoded-file-content",
    "language": "english",
    "subtitle_language": "english",
    "generate_avatar": true,
    "generate_subtitles": true
  }
  ```
- `language`: Audio language (default: "english")
- `subtitle_language`: Subtitle language (optional)
- `generate_avatar`: Whether to generate AI avatar (default: true)
- `generate_subtitles`: Whether to generate subtitles (default: true)

**Response:**
```json
{
  "file_id": "string",
  "task_id": "string",
  "message": "File uploaded successfully, processing started in background"
}
```

### Get Processing Progress

```
GET /api/progress/{file_id}
```

Get detailed progress information for a presentation processing task.

**Response:**
```json
{
  "status": "uploaded|processing|completed|failed|not_found",
  "progress": 0-100,
  "current_step": "string",
  "steps": {
    "extract_slides": {"status": "pending|processing|completed|failed", "data": null|object},
    "convert_slides_to_images": {"status": "pending|processing|completed|failed", "data": null|object},
    "analyze_slide_images": {"status": "pending|processing|completed|failed", "data": null|object},
    "generate_scripts": {"status": "pending|processing|completed|failed", "data": null|object},
    "review_scripts": {"status": "pending|processing|completed|failed", "data": null|object},
    "generate_audio": {"status": "pending|processing|completed|failed", "data": null|object},
    "generate_avatar_videos": {"status": "pending|processing|completed|failed", "data": null|object},
    "compose_video": {"status": "pending|processing|completed|failed", "data": null|object}
  },
  "errors": [],
  "created_at": "ISO timestamp",
  "updated_at": "ISO timestamp"
}
```

### Download Completed Video

```
GET /api/video/{file_id}
```

Download the completed video presentation.

**Response:**
- Video file (MP4 format) or 404 if not found

### Get Video URL

```
GET /api/video/{file_id}/url
```

Get a presigned URL for the completed video presentation. This endpoint returns a temporary URL that can be used to download the video directly from the storage provider.

**Response:**
```json
{
  "url": "string",
  "expires_in": "integer"
}
```

### Download Subtitles

```
GET /api/subtitles/{file_id}/srt
GET /api/subtitles/{file_id}/vtt
```

Download subtitle files for the completed video.

**Response:**
- SRT or VTT subtitle file or 404 if not found

### Get Subtitle URL

```
GET /api/subtitles/{file_id}/{lang}/srt/url
GET /api/subtitles/{file_id}/{lang}/vtt/url
```

Get a presigned URL for subtitle files. This endpoint returns a temporary URL that can be used to download the subtitles directly from the storage provider.

**Response:**
```json
{
  "url": "string",
  "expires_in": "integer"
}
```

## Task Monitoring Endpoints

### List All Tasks

```
GET /api/tasks
```

Get a list of all tasks with optional filtering and pagination.

**Query Parameters:**
- `status` (optional): Filter by task status (queued, processing, completed, failed, cancelled)
- `limit` (optional, default: 50): Maximum number of tasks to return (1-1000)
- `offset` (optional, default: 0): Number of tasks to skip
- `sort_by` (optional, default: "created_at"): Sort field (created_at, updated_at, status)
- `sort_order` (optional, default: "desc"): Sort order (asc, desc)

**Response:**
```json
{
  "tasks": [
    {
      "task_id": "string",
      "task_type": "string",
      "status": "queued|processing|completed|failed|cancelled",
      "kwargs": {},
      "result": null|object,
      "error": null|string,
      "file_id": "string",
      "state": {
        "status": "uploaded|processing|completed|failed|cancelled",
        "current_step": "string",
        "voice_language": "string",
        "subtitle_language": "string",
        "generate_avatar": true|false,
        "generate_subtitles": true|false,
        "created_at": "ISO timestamp",
        "updated_at": "ISO timestamp",
        "errors": []
      }
    }
  ],
  "total": "integer",
  "limit": "integer",
  "offset": "integer",
  "has_more": true|false
}
```

### Search Tasks

```
GET /api/tasks/search
```

Search for tasks by file ID or other properties.

**Query Parameters:**
- `query` (required): Search query for file ID or task properties
- `limit` (optional, default: 20): Maximum number of results (1-100)

**Response:**
```json
{
  "tasks": [
    // Array of task objects (same format as /api/tasks)
  ],
  "query": "string",
  "total_found": "integer"
}
```

### Get Task Statistics

```
GET /api/tasks/statistics
```

Get comprehensive statistics about all tasks.

**Response:**
```json
{
  "total_tasks": "integer",
  "status_breakdown": {
    "queued": "integer",
    "processing": "integer",
    "completed": "integer",
    "failed": "integer",
    "cancelled": "integer"
  },
  "language_stats": {
    "english": "integer",
    "chinese": "integer",
    // ... other languages
  },
  "recent_activity": {
    "last_24h": "integer",
    "last_7d": "integer",
    "last_30d": "integer"
  },
  "processing_stats": {
    "avg_processing_time_minutes": "number|null",
    "success_rate": "number",
    "failed_rate": "number"
  }
}
```

### Get Task Details

```
GET /api/tasks/{task_id}
```

Get detailed information about a specific task.

**Response:**
```json
{
  "task_id": "string",
  "file_id": "string",
  "task_type": "string",
  "status": "queued|processing|completed|failed|cancelled",
  "kwargs": {},
  "result": null|object,
  "error": null|string,
  "created_at": "ISO timestamp",
  "updated_at": "ISO timestamp",
  "detailed_state": {
    "file_id": "string",
    "file_path": "string",
    "file_ext": "string",
    "voice_language": "string",
    "subtitle_language": "string",
    "generate_avatar": true|false,
    "generate_subtitles": true|false,
    "status": "uploaded|processing|completed|failed|cancelled",
    "current_step": "string",
    "steps": {
      "extract_slides": {"status": "pending|processing|completed|failed|skipped|cancelled", "data": null|object},
      "convert_slides_to_images": {"status": "pending|processing|completed|failed|skipped|cancelled", "data": null|object},
      "analyze_slide_images": {"status": "pending|processing|completed|failed|skipped|cancelled", "data": null|object},
      "generate_scripts": {"status": "pending|processing|completed|failed|skipped|cancelled", "data": null|object},
      "review_scripts": {"status": "pending|processing|completed|failed|skipped|cancelled", "data": null|object},
      "generate_audio": {"status": "pending|processing|completed|failed|skipped|cancelled", "data": null|object},
      "generate_avatar_videos": {"status": "pending|processing|completed|failed|skipped|cancelled", "data": null|object},
      "generate_subtitles": {"status": "pending|processing|completed|failed|skipped|cancelled", "data": null|object},
      "compose_video": {"status": "pending|processing|completed|failed|skipped|cancelled", "data": null|object}
    },
    "created_at": "ISO timestamp",
    "updated_at": "ISO timestamp",
    "errors": []
  },
  "completion_percentage": "integer"
}
```

### Cancel Task

```
DELETE /api/tasks/{task_id}
```

Cancel a specific task if it's still running.

**Response:**
```json
{
  "message": "Task cancelled successfully",
  "task_id": "string",
  "file_id": "string"
}
```

**Error Response:**
- 400: Task cannot be cancelled (already completed or not found)
- 500: Failed to cancel task

## Processing Steps

1. **extract_slides** - Extract content from the presentation file
2. **convert_slides_to_images** - Convert slides to image format
3. **analyze_slide_images** - Analyze visual content using AI
4. **generate_scripts** - Generate AI narratives for each slide
5. **review_scripts** - Review and refine scripts for consistency
6. **generate_audio** - Create text-to-speech audio files
7. **generate_avatar_videos** - Generate AI avatar videos (skipped if generate_avatar=false)
8. **generate_subtitles** - Generate subtitle files for the video
9. **compose_video** - Compose final video presentation

## Error Handling

The API provides detailed error information in the progress endpoint under the `errors` array. Each error includes:
- `step`: The processing step where the error occurred
- `error`: Description of the error
- `timestamp`: When the error occurred

## Additional Endpoints

### Get Supported Languages

```
GET /api/languages
```

Get a list of supported languages for content generation and subtitles.

**Response:**
```json
{
  "content_languages": ["english", "chinese", "japanese", "korean", "thai"],
  "subtitle_languages": ["english", "chinese", "japanese", "korean", "thai"]
}
```

## Unified Storage System

The API features a unified storage system that supports multiple storage providers:

- **Local Filesystem**: Default option, stores files in the `output/` directory
- **AWS S3**: Cloud storage option for scalable hosting
- **Aliyun OSS**: Alternative cloud storage option, particularly useful in China

### Storage Provider Configuration

The system automatically selects the appropriate storage provider based on the `STORAGE_PROVIDER` environment variable:
- `local`: Files are stored in the local filesystem under the `output/` directory
- `s3`: Files are stored in AWS S3 (requires AWS configuration)
- `oss`: Files are stored in Aliyun OSS (requires OSS configuration)

### Automatic Fallback

If cloud storage upload fails, the system automatically falls back to local storage to ensure file availability.

### Presigned URLs

All storage providers support presigned URL generation for secure file access, allowing users to download files without exposing credentials. The `/url` endpoints provide temporary URLs that can be used to download files directly from the storage provider.

### Locale-aware Subtitle Filenames

The system generates locale-aware subtitle filenames (e.g., `_en.srt`, `_zh-Hans.vtt`) for better internationalization support while maintaining backward compatibility with legacy formats.

### Storage Path Configuration

You can customize the storage paths using environment variables:
- `OUTPUT_DIR`: Directory for storing output files (default: `api/output`)
- `UPLOADS_DIR`: Directory for storing uploaded files (default: `api/uploads`)

## Service Configuration

The API now supports multiple AI service providers. The system will automatically use available services based on configured API keys:

### Supported Services
- **Script Generation**: OpenAI GPT models or Qwen
- **Text-to-Speech**: OpenAI TTS, ElevenLabs, or local TTS
- **Avatar Generation**: HeyGen for realistic avatars or DALL-E for custom AI-generated presenters

## Memory Optimization Features

### Video Composition Improvements
Recent API enhancements include memory-optimized video processing:

- **Memory-efficient processing**: Videos are processed one slide at a time to prevent memory exhaustion
- **Video validation**: Avatar videos are automatically validated for corruption before processing
- **Error recovery**: Failed slides are skipped gracefully without affecting other slides
- **Timeout protection**: 30-minute timeout prevents hanging processes
- **Progress feedback**: Real-time progress updates during video composition
- **Watermark integration**: Automatic watermarking of final videos

### Enhanced Error Reporting
- **Memory-related errors**: Detailed reporting when video processing exceeds memory limits
- **Corrupted video detection**: Specific error messages for corrupted avatar videos
- **Timeout notifications**: Clear indication when video processing times out
- **Resource cleanup**: Confirmation of cleanup operations after task cancellation

## Task Monitoring and Management

SlideSpeaker includes comprehensive task monitoring capabilities that allow users and administrators to track, search, and analyze processing tasks.

### Monitoring Features

- **Task listing**: View all tasks with filtering and pagination options
- **Task search**: Search for specific tasks by file ID or properties
- **Detailed statistics**: Get comprehensive statistics on task processing
- **Individual task details**: View detailed information about specific tasks
- **Task cancellation**: Cancel specific tasks through API endpoints

### Statistics and Analytics

The system provides detailed analytics on:
- **Task status distribution**: Breakdown of tasks by status (queued, processing, completed, failed, cancelled)
- **Language usage**: Statistics on content languages used
- **Processing performance**: Average processing times and success/failure rates
- **Recent activity**: Task volume over time (last 24 hours, 7 days, 30 days)

## State Management Features

### Task State Persistence
- **Local Storage**: Frontend automatically saves task state to prevent data loss on page refresh
- **Recovery**: Task progress is restored when users return to the application
- **Session Management**: Upload history and download links are maintained across sessions

## Watermark Integration

All generated videos automatically include a watermark for branding and protection. The watermark is highly visible and positioned in the bottom-right corner of the video.

### Watermark Configuration

The watermark can be configured using the following environment variables:
- `WATERMARK_ENABLED`: Enable or disable watermark (default: true)
- `WATERMARK_TEXT`: Text to display in the watermark (default: "SlideSpeaker AI")
- `WATERMARK_OPACITY`: Opacity of the watermark (0.0-1.0, default: 0.95)
- `WATERMARK_SIZE`: Font size of the watermark in pixels (default: 64)

### Watermark Features

- **High visibility**: Thick stroke and high contrast for maximum visibility
- **Positioning**: Fixed position in bottom-right corner of the video
- **Scalability**: Automatically sized based on video dimensions
- **Memory efficient**: Optimized for long videos without memory issues
- **Fallback support**: Multiple fallback mechanisms for font compatibility