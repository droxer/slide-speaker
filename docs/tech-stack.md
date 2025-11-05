# Backend Technical Stack

## Overview

The SlideSpeaker backend is a high-performance API server built with Python FastAPI, designed to handle AI-powered media processing tasks. The system follows a microservices architecture with Redis for task queuing and state management, supporting multiple AI providers and cloud storage solutions.

## Core Technologies

### Framework & Language
- **Python 3.12+** - Modern Python version with enhanced performance
- **FastAPI** - High-performance web framework with automatic API documentation
- **uv** - Ultra-fast Python package installer and resolver

### Task Management
- **Redis** - In-memory data structure store for task queuing and state management
- **Master-Worker Architecture** - Scalable processing with multiple worker processes
- **Asyncio** - Asynchronous programming for non-blocking operations

### AI Services Integration
- **OpenAI** - Primary LLM provider for script generation, TTS, and vision processing
- **ElevenLabs** - Alternative TTS provider for enhanced voice synthesis
- **HeyGen** - AI avatar generation service
- **DALL-E** - Image generation (fallback for avatar generation)

### Media Processing
- **FFmpeg** - Comprehensive multimedia framework for video/audio processing
- **MoviePy** - Python library for video editing and compositing
- **Pillow** - Python Imaging Library for image manipulation
- **Pydub** - Audio processing and manipulation
- **LibreOffice** - Document conversion (PPT/PPTX to PDF)

### Storage Solutions
- **Local Filesystem** - Built-in storage option
- **AWS S3** - Cloud object storage (optional)
- **Aliyun OSS** - Alternative cloud storage (optional)
- **Unified Storage Interface** - Abstraction layer for multiple providers

## Architecture

### System Components

#### API Server (`api/server.py`)
- **RESTful API** - HTTP endpoints for all application functionality
- **WebSocket Support** - Real-time communication for progress updates
- **Authentication** - JWT-based user authentication
- **Rate Limiting** - Request throttling for API protection
- **Monitoring** - Performance metrics and health checks

#### Master Worker (`api/master_worker.py`)
- **Worker Management** - Spawns and monitors processing workers
- **Load Balancing** - Distributes tasks across available workers
- **Health Monitoring** - Tracks worker status and performance
- **Auto-scaling** - Dynamic worker adjustment based on queue depth

#### Task Workers (`api/worker.py`)
- **Task Processing** - Executes media processing pipelines
- **Step-based Execution** - Modular processing with progress tracking
- **Error Handling** - Robust error recovery and logging
- **Resource Management** - Efficient memory and CPU usage

### Core Modules (`api/slidespeaker/`)

#### Core Layer (`slidespeaker/core/`)
- **Task Queue** - Redis-based queuing system with priority support
- **State Manager** - Persistent task state tracking and management
- **Monitoring** - Performance metrics collection and reporting
- **Rate Limiting** - Request throttling using slowapi library

#### Routes Layer (`slidespeaker/routes/`)
- **Upload Routes** - File upload handling and validation
- **Task Routes** - Task creation, management, and status
- **Download Routes** - Asset delivery and streaming
- **Transcript Routes** - Subtitle and transcript management
- **Stats Routes** - Analytics and reporting endpoints
- **Metrics Routes** - Performance monitoring endpoints
- **Auth Routes** - User authentication and session management

#### Pipeline Layer (`slidespeaker/pipeline/`)
- **PDF Coordinator** - Specialized processing for PDF documents
- **Slides Coordinator** - Specialized processing for presentation slides
- **Step Orchestration** - Coordinated execution of processing steps
- **Task Routing** - Intelligent task distribution based on content type

#### Processing Layer (`slidespeaker/processing/`)
- **Audio Processing** - Voice synthesis and audio manipulation
- **Video Processing** - Video composition and editing
- **Subtitle Processing** - Caption generation and formatting
- **Image Processing** - Avatar generation and image optimization
- **Waveform Generation** - Audio visualization for podcast players

#### Services Layer (`slidespeaker/services/`)
- **OpenAI Client** - Centralized OpenAI API integration
- **ElevenLabs Client** - ElevenLabs TTS service integration
- **HeyGen Client** - HeyGen avatar generation integration
- **Vision Services** - Image analysis and processing
- **TTS Services** - Text-to-speech processing

#### LLM Layer (`slidespeaker/llm/`)
- **Chat Completion** - Centralized chat API with retry logic
- **Image Generation** - DALL-E integration with error handling
- **TTS Streaming** - Streaming text-to-speech synthesis
- **Prompt Management** - Template-based prompt construction

#### Storage Layer (`slidespeaker/storage/`)
- **Local Storage** - Filesystem-based storage implementation
- **AWS S3** - Amazon S3 integration (optional)
- **Aliyun OSS** - Alibaba Cloud OSS integration (optional)
- **Storage Interface** - Unified API for all storage providers

#### Configs Layer (`slidespeaker/configs/`)
- **Environment Management** - Configuration loading and validation
- **Settings** - Application settings and defaults
- **Feature Flags** - Conditional feature activation

## Key Libraries & Dependencies

### Web Framework
- **FastAPI** - ASGI web framework with automatic OpenAPI documentation
- **Uvicorn** - ASGI server implementation
- **Starlette** - ASGI toolkit (used by FastAPI)
- **Pydantic** - Data validation and settings management

### Database & Caching
- **Redis** - In-memory data structure store
- **redis-py** - Python Redis client
- **asyncio-redis** - Async Redis client (future enhancement)

### AI & Media Processing
- **openai** - Official OpenAI Python library
- **elevenlabs** - ElevenLabs Python library
- **requests** - HTTP library for API calls
- **ffmpeg-python** - Python bindings for FFmpeg
- **moviepy** - Video editing with Python
- **Pillow** - Python Imaging Library
- **pydub** - Audio manipulation library

### Storage
- **boto3** - AWS SDK for Python (S3 support)
- **oss2** - Aliyun OSS SDK for Python
- **aiofiles** - Async file operations

### Utilities
- **python-multipart** - Multipart form parsing
- **python-jose** - JWT implementation
- **passlib** - Password hashing
- **slowapi** - Rate limiting for FastAPI
- **python-dotenv** - Environment variable management

## Task Processing Pipeline

### Processing Steps
1. **File Analysis** - Content type detection and validation
2. **Script Generation** - AI-powered script creation from content
3. **Voice Synthesis** - Text-to-speech conversion with multiple providers
4. **Avatar Generation** - AI avatar creation (optional)
5. **Video Composition** - Media assembly and editing
6. **Subtitle Generation** - Caption creation in multiple languages
7. **Quality Assurance** - Final validation and optimization

### Error Handling & Recovery
- **Retry Logic** - Configurable retry mechanisms for transient failures
- **Circuit Breaker** - Protection against cascading failures
- **Graceful Degradation** - Fallback options for failed steps
- **Comprehensive Logging** - Detailed error tracking and debugging

## Performance Optimizations

### Concurrency
- **Async/Await** - Non-blocking I/O operations
- **Thread Pools** - CPU-bound task parallelization
- **Process Pools** - Memory isolation for heavy processing
- **Connection Pooling** - Efficient database and API connections

### Caching
- **Redis Caching** - In-memory data caching
- **Response Caching** - HTTP response caching
- **Computation Caching** - Expensive operation results caching

### Resource Management
- **Memory Optimization** - Efficient data structure usage
- **Streaming** - Chunked data processing to reduce memory footprint
- **Garbage Collection** - Explicit resource cleanup

## Security Features

### Authentication & Authorization
- **JWT Tokens** - Secure session management
- **Role-based Access** - Granular permission control
- **Token Expiration** - Automatic session invalidation
- **Refresh Tokens** - Seamless session renewal

### Data Protection
- **Encryption at Rest** - Sensitive data encryption
- **HTTPS Enforcement** - TLS requirement for all communications
- **Input Validation** - Comprehensive data sanitization
- **Rate Limiting** - Protection against abuse

### API Security
- **CORS Configuration** - Controlled cross-origin requests
- **Content Security** - Request size and type validation
- **Audit Logging** - Security-relevant event tracking
- **Vulnerability Scanning** - Regular security assessments

## Monitoring & Observability

### Metrics Collection
- **Performance Metrics** - Response times, throughput, error rates
- **Resource Usage** - CPU, memory, disk, and network utilization
- **Business Metrics** - Task completion rates, user activity
- **Custom Metrics** - Application-specific measurements

### Health Checks
- **System Health** - Overall system status monitoring
- **Service Health** - Individual component status
- **Dependency Health** - External service availability
- **Automatic Recovery** - Self-healing mechanisms

### Logging
- **Structured Logging** - JSON-formatted log entries
- **Log Levels** - Configurable verbosity (DEBUG, INFO, WARNING, ERROR)
- **Log Aggregation** - Centralized log collection
- **Log Rotation** - Automatic log file management

## Development Workflow

### Scripts
- `make dev` - Start development server with auto-reload
- `make start` - Start production server
- `make master-worker` - Start master process with workers
- `make lint` - Run Ruff linter
- `make format` - Run Ruff formatter
- `make typecheck` - Run mypy type checker
- `make check` - Run linting and type checking
- `make test` - Run unit tests

### Code Quality
- **Ruff** - Fast Python linter and formatter
- **mypy** - Static type checking
- **pre-commit** - Git hooks for code quality
- **pytest** - Testing framework

### Testing
- **Unit Tests** - Component-level testing
- **Integration Tests** - Cross-component testing
- **API Tests** - HTTP endpoint validation
- **Load Testing** - Performance benchmarking

## Deployment Architecture

### Scalability
- **Horizontal Scaling** - Multiple worker processes
- **Load Distribution** - Task queue-based workload balancing
- **Resource Isolation** - Process-based resource separation
- **Auto-scaling** - Dynamic worker adjustment

### Containerization
- **Docker Support** - Containerized deployment
- **Multi-stage Builds** - Optimized container images
- **Environment Configuration** - Container-friendly settings
- **Health Checks** - Container orchestration integration

### Cloud Deployment
- **AWS Deployment** - EC2, ECS, and Lambda support
- **Aliyun Deployment** - ECS and Function Compute support
- **Kubernetes** - Container orchestration ready
- **Serverless** - Function-as-a-Service deployment

### Backup & Recovery
- **Data Backup** - Regular data snapshots
- **Disaster Recovery** - Automated recovery procedures
- **Rollback Capability** - Versioned deployments
- **Data Integrity** - Checksum validation and verification