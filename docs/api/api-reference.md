# SlideSpeaker API Reference

## Overview

The SlideSpeaker API provides endpoints for converting presentation files (PDF, PowerPoint) into narrated videos with features like transcripts, text-to-speech (TTS), subtitles, and optional AI avatars. The API uses JWT-based authentication and follows RESTful principles.

## Authentication

Most endpoints require authentication using JWT tokens. Include the token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

## Base URL

All API endpoints are prefixed with `/api/`.

## Endpoints

### Authentication

#### POST `/api/auth/register`
Register a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "name": "John Doe"
}
```

**Response:**
```json
{
  "user": {
    "id": "user-id",
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

#### POST `/api/auth/login`
Authenticate a user and receive a JWT token.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response:**
```json
{
  "user": {
    "id": "user-id",
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

#### POST `/api/auth/oauth/google`
Authenticate using Google OAuth.

**Request Body:**
```json
{
  "email": "user@example.com",
  "id": "google-id",
  "name": "John Doe",
  "picture": "https://example.com/pic.jpg"
}
```

### File Upload

#### POST `/api/upload`
Upload a presentation file and start processing.

**Request Headers:**
- `Authorization: Bearer <token>`

**Request (Multipart Form):**
- `file`: The presentation file (PDF, PPTX, PPT)
- `voice_language`: Language for voice generation (default: english)
- `subtitle_language`: Language for subtitles (optional)
- `transcript_language`: Language for transcript (optional)
- `video_resolution`: Resolution (sd, hd, fullhd) (default: hd)
- `generate_avatar`: Whether to generate avatar (default: false)
- `generate_subtitles`: Whether to generate subtitles (default: true)
- `generate_podcast`: Whether to generate podcast (default: false)
- `generate_video`: Whether to generate video (default: true)
- `task_type`: Task type (video, podcast, both) (optional)
- `source_type`: Source type (pdf, slides, audio) (optional)
- `voice_id`: Specific voice ID to use
- `podcast_host_voice`: Voice for podcast host
- `podcast_guest_voice`: Voice for podcast guest

**Response:**
```json
{
  "file_id": "unique-file-id",
  "task_id": "unique-task-id",
  "message": "File uploaded successfully, processing started in background"
}
```

#### GET `/api/uploads`
List uploads for the authenticated user.

**Request Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "uploads": [
    {
      "id": "upload-id",
      "user_id": "user-id",
      "filename": "presentation.pdf",
      "file_ext": ".pdf",
      "source_type": "pdf",
      "content_type": "application/pdf",
      "checksum": "sha256-checksum",
      "size_bytes": 123456,
      "storage_path": "/path/to/storage",
      "created_at": "2023-01-01T00:00:00Z",
      "updated_at": "2023-01-01T00:00:00Z"
    }
  ]
}
```

### Task Management

#### GET `/api/tasks`
List tasks for the authenticated user.

**Request Headers:**
- `Authorization: Bearer <token>`

**Query Parameters:**
- `status`: Filter by task status
- `limit`: Max number of tasks to return (default: 50, max: 1000)
- `offset`: Number of tasks to skip (default: 0)
- `sort_by`: Sort field (created_at, updated_at, status) (default: created_at)
- `sort_order`: Sort order (asc, desc) (default: desc)

**Response:**
```json
{
  "tasks": [
    {
      "id": "task-id",
      "task_id": "task-id",
      "upload_id": "upload-id",
      "task_type": "video",
      "status": "completed",
      "kwargs": {},
      "error": null,
      "user_id": "user-id",
      "voice_language": "english",
      "subtitle_language": "english",
      "source_type": "pdf",
      "created_at": "2023-01-01T00:00:00Z",
      "updated_at": "2023-01-01T00:00:00Z",
      "filename": "presentation.pdf",
      "file_ext": ".pdf"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0,
  "has_more": false
}
```

#### GET `/api/tasks/{task_id}/status`
Get the status of a specific task.

**Request Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "task_id": "task-id",
  "status": "processing",
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z",
  "kwargs": {},
  "user_id": "user-id"
}
```

#### GET `/api/tasks/{task_id}`
Get simplified information about a specific task optimized for frontend display.
Only queries database (no Redis state) to ensure consistent and performant responses.

**Request Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "task_id": "task-id",
  "status": "completed",
  "task_type": "video", 
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z",
  "filename": "presentation.pdf",
  "file_ext": ".pdf",
  "source_type": "pdf", 
  "voice_language": "english",
  "subtitle_language": "english",
  "generate_podcast": false,
  "generate_video": true,
  "completion_percentage": 100,
  "downloads": {
    "video_url": "/api/video/file-id",
    "audio_url": "/api/audio/file-id", 
    "subtitle_url": "/api/subtitles/file-id",
    "transcript_url": "/api/download-transcript/file-id"
  }
}
```

**Note**: This endpoint queries only the database (not Redis) and returns a simplified payload optimized for the frontend TaskDetailPage. This ensures consistent, performant responses with only essential information needed for task display, media preview, language information, and download options.

#### POST `/api/tasks/{task_id}/cancel`
Cancel a running task.

**Request Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "message": "Task cancelled successfully"
}
```

#### POST `/api/tasks/{task_id}/retry`
Retry a failed task from a specific step.

**Request Headers:**
- `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "step": "optional-step-name"
}
```

**Response:**
```json
{
  "message": "Task retry queued",
  "step": "step-name",
  "status": "processing"
}
```

#### DELETE `/api/tasks/{task_id}/delete`
Delete a task and its associated files from database and storage.

**Request Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "message": "Task task-id deleted successfully"
}
```

**Note**: This endpoint performs complete task removal, including cancellation in the queue, database deletion, Redis cleanup, and triggering asynchronous file purging from storage.

#### GET `/api/tasks/search`
Search across tasks.

**Request Headers:**
- `Authorization: Bearer <token>`

**Query Parameters:**
- `query`: Search query for task_id, file_id, status, task_type, or kwargs
- `limit`: Max number of results (default: 20, max: 100)

**Response:**
```json
{
  "tasks": [...],
  "query": "search-term",
  "total_found": 1
}
```

#### GET `/api/tasks/statistics`
Get comprehensive statistics about all tasks.

**Request Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "total_tasks": 10,
  "status_breakdown": {
    "completed": 7,
    "processing": 2,
    "failed": 1
  },
  "language_stats": {
    "english": 8,
    "spanish": 2
  },
  "recent_activity": {
    "last_24h": 3,
    "last_7d": 10,
    "last_30d": 15
  },
  "processing_stats": {
    "avg_processing_time_minutes": 5.5,
    "success_rate": 0.9,
    "failed_rate": 0.1
  }
}
```

### Progress Tracking

#### GET `/api/tasks/{task_id}/progress`
Get detailed progress information about a task.

**Request Headers:**
- `Authorization: Bearer <token>`

**Query Parameters:**
- `view`: View type (compact)

**Response:**
```json
{
  "status": "processing",
  "progress": 65,
  "current_step": "generating_video",
  "steps": {
    "parse_document": {
      "status": "completed"
    },
    "generate_transcript": {
      "status": "completed"
    },
    "generate_audio": {
      "status": "processing"
    },
    "generate_video": {
      "status": "pending"
    }
  },
  "errors": [],
  "filename": "presentation.pdf",
  "file_ext": ".pdf",
  "source_type": "pdf",
  "voice_language": "english",
  "subtitle_language": "english",
  "generate_podcast": false,
  "generate_video": true,
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

### Downloads

#### GET `/api/download/{file_id}`
Download the generated video file.

**Request Headers:**
- `Authorization: Bearer <token>`

#### GET `/api/download-avatar/{file_id}`
Download the avatar video.

**Request Headers:**
- `Authorization: Bearer <token>`

#### GET `/api/download-audio/{file_id}`
Download the audio file.

**Request Headers:**
- `Authorization: Bearer <token>`

#### GET `/api/download-subtitle/{file_id}`
Download the subtitle file (VTT format).

**Request Headers:**
- `Authorization: Bearer <token>`

#### GET `/api/subtitles/{file_id}`
Download subtitles in SRT format.

**Request Headers:**
- `Authorization: Bearer <token>`

#### GET `/api/video/{file_id}`
Download the final video.

**Request Headers:**
- `Authorization: Bearer <token>`

#### GET `/api/audio/{file_id}`
Download the audio file.

**Request Headers:**
- `Authorization: Bearer <token>`

### Audio

#### GET `/api/audio/voices`
Get available voice options for TTS.

**Request Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "voices": [
    {
      "id": "voice-id",
      "name": "Voice Name",
      "language": "en",
      "gender": "male"
    }
  ]
}
```

### Podcast

#### POST `/api/podcast/generate`
Generate a podcast from a document.

**Request Headers:**
- `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "file_id": "file-id",
  "host_voice": "voice-id",
  "guest_voice": "voice-id",
  "transcript": "optional transcript text"
}
```

### Languages

#### GET `/api/languages`
Get available language options.

**Request Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "languages": [
    {
      "code": "en",
      "name": "English",
      "native_name": "English"
    }
  ]
}
```

### Health

#### GET `/api/health`
Get system health information.

**Response:**
```json
{
  "status": "ok",
  "redis": {
    "ok": true,
    "latency_ms": 2.5
  },
  "db": {
    "ok": true,
    "latency_ms": 5.2
  }
}
```

### Statistics

#### GET `/api/stats`
Get system statistics.

**Request Headers:**
- `Authorization: Bearer <token>`

### Users

#### GET `/api/users/me`
Get current user profile.

**Request Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "user": {
    "id": "user-id",
    "email": "user@example.com",
    "name": "John Doe",
    "preferred_language": "en",
    "preferred_theme": "light"
  }
}
```

#### PATCH `/api/users/me`
Update current user profile.

**Request Headers:**
- `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "New Name",
  "preferred_language": "es",
  "preferred_theme": "dark"
}
```

## File Types Supported

- PDF documents
- PowerPoint presentations (.pptx, .ppt)
- Audio files (.mp3, .wav, .m4a, .aac, .flac) for podcast generation

## Rate Limits

The API enforces rate limits to prevent abuse:

- Upload: 5/minute per IP
- Task status: 30/minute per IP
- Task cancellation: 10/minute per IP
- Registration: 5/minute per IP
- Login: 10/minute per IP
- OAuth: 10/minute per IP

## Error Handling

The API returns standard HTTP status codes:

- `200`: Success
- `201`: Created
- `400`: Bad request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not found
- `409`: Conflict (e.g., duplicate email)
- `413`: Request entity too large
- `429`: Too many requests
- `500`: Internal server error

Error responses follow this format:
```json
{
  "detail": "Error message"
}
```