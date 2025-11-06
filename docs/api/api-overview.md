# SlideSpeaker API Overview

## Introduction

The SlideSpeaker API is a comprehensive backend service that transforms presentation files (PDF, PowerPoint) into narrated videos with advanced features like transcripts, text-to-speech (TTS), subtitles, and optional AI avatars. Built with FastAPI, the API provides a robust and scalable solution for automated presentation processing.

## Architecture

The API follows a microservice-like architecture with clear separation of concerns:

- **FastAPI Application**: Main web server handling HTTP requests
- **Task Queue**: Redis-based queue system for background processing
- **Worker Processes**: Dedicated processes for CPU-intensive tasks
- **Database**: PostgreSQL for persistent data storage
- **Storage**: Multiple backends (local, AWS S3, Aliyun OSS) for file storage
- **Authentication**: JWT-based user management system

## Core Functionality

### 1. Document Processing Pipeline
The API processes presentation files through a multi-step pipeline:

1. **Upload**: Accept presentation files (PDF, PPTX, PPT)
2. **Parsing**: Extract content and structure from documents
3. **Transcription**: Generate scripts from slide content using AI
4. **Text-to-Speech**: Convert text to natural-sounding audio
5. **Video Generation**: Combine audio with slides and optional avatars
6. **Subtitle Creation**: Generate SRT/VTT subtitles synchronized with narration
7. **Output Delivery**: Provide downloadable media files

### 2. Task Management
- Asynchronous processing to handle long-running operations
- Real-time progress tracking for users
- Task cancellation and retry functionality
- Detailed error reporting and recovery

### 3. Content Generation Options
- **Video**: Full presentation-to-video conversion
- **Podcast**: Audio-only content generation
- **Avatar Integration**: AI-generated presenter avatars
- **Multi-language Support**: Voice, subtitle, and transcript languages
- **Subtitle Formats**: Both VTT and SRT formats available

## Authentication & Authorization

The API implements secure authentication using:

- JWT tokens for session management
- OAuth2 password flow for login
- Google OAuth integration
- User permission validation for all endpoints
- Rate limiting to prevent abuse

## Rate Limiting

The API enforces rate limits per IP address to ensure fair usage and system stability:

- Registration: 5 requests/minute
- Login: 10 requests/minute
- OAuth: 10 requests/minute
- Upload: 5 requests/minute
- Task status: 30 requests/minute
- Task cancellation: 10 requests/minute

## Data Flow

1. **Upload Request**: Client uploads a presentation file
2. **Task Creation**: API creates a task record and adds to queue
3. **Background Processing**: Worker processes the file through pipeline
4. **Progress Tracking**: State updates are stored and reported
5. **Result Delivery**: Processed files are stored and made available for download

## API Security

- All endpoints require authentication (except health checks)
- Request validation and sanitization
- Secure file upload handling with size limits (100 MB)
- SQL injection prevention through ORM usage
- Cross-site scripting (XSS) protection through proper output encoding

## Error Handling

The API provides detailed error responses to help clients handle issues appropriately:

- Standard HTTP status codes
- Descriptive error messages
- Structured error objects for complex failures
- Fallback mechanisms for storage and database operations

## Performance & Scalability

- Redis for fast, distributed task queue management
- Asynchronous processing to handle multiple requests
- Optional database caching for frequently accessed data
- Configurable worker count for parallel processing
- Efficient file storage and retrieval mechanisms

## Integration Points

The API connects to various external services:

- **AI Services**: OpenAI, ElevenLabs, Google Gemini for LLM and TTS
- **Storage Services**: AWS S3, Aliyun OSS for cloud storage
- **Database Services**: PostgreSQL for persistent storage
- **Authentication**: Google OAuth for social login

## Monitoring & Observability

- Request logging with structured format
- Performance monitoring for API endpoints
- Task processing metrics and statistics
- Health checks for system components (Redis, Database)

## Client Integration

To integrate with the SlideSpeaker API, clients should:

1. Register or authenticate users
2. Upload presentation files using the upload endpoint
3. Monitor task progress using the progress endpoints
4. Download results when processing is complete
5. Handle errors gracefully with appropriate retry logic

This API provides a complete solution for converting static presentations into engaging video content with minimal manual intervention, making it ideal for educational, corporate, and content creation use cases.