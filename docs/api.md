# API Documentation

## Base URL

All API endpoints are relative to: `http://localhost:8000/api`

## Endpoints

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

### Download Subtitles

```
GET /api/subtitles/{file_id}/srt
GET /api/subtitles/{file_id}/vtt
```

Download subtitle files for the completed video.

**Response:**
- SRT or VTT subtitle file or 404 if not found

### Get Task Status

```
GET /api/task/{task_id}
```

Get the status of a background processing task.

**Response:**
```json
{
  "task_id": "string",
  "task_type": "string",
  "status": "queued|processing|completed|failed",
  "kwargs": {},
  "result": null|object,
  "error": null|string
}
```

### Cancel Task Processing

```
POST /api/task/{task_id}/cancel
```

Cancel a background processing task. If the task is queued, it will be removed from the queue. If the task is currently processing, it will be marked for cancellation and will stop at the next checkpoint.

**Response:**
```json
{
  "message": "Task cancelled successfully"
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
7. **generate_avatar_videos** - Generate AI avatar videos
8. **compose_video** - Compose final video presentation

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

### Enhanced Error Reporting
- **Memory-related errors**: Detailed reporting when video processing exceeds memory limits
- **Corrupted video detection**: Specific error messages for corrupted avatar videos
- **Timeout notifications**: Clear indication when video processing times out
- **Resource cleanup**: Confirmation of cleanup operations after task cancellation

## State Management Features

### Task State Persistence
- **Local Storage**: Frontend automatically saves task state to prevent data loss on page refresh
- **Recovery**: Task progress is restored when users return to the application
- **Session Management**: Upload history and download links are maintained across sessions