# Architecture Overview

SlideSpeaker uses a distributed microservices architecture with clear separation of concerns:

```
┌─────────────────┐    HTTP Requests    ┌──────────────────┐
│   Web Client    │ ──────────────────▶ │   API Server     │
│  (React App)    │                     │  (server.py)     │
└─────────────────┘                     └──────────────────┘
                                                 │
                                                 ▼
                                       ┌──────────────────┐
                                       │  Task Queue      │
                                       │   (Redis)        │
                                       └──────────────────┘
                                                 │
                                                 ▼
                             ┌─────────────────────────────────┐
                             │     Master Worker               │
                             │   (master_worker.py)            │
                             └─────────────────────────────────┘
                                                 │
                   ┌─────────────────┬─────────────┬─────────────────┐
                   ▼                 ▼             ▼                 ▼
         ┌──────────────────┐ ┌──────────────────┐ ...    ┌──────────────────┐
         │  Task Worker 1   │ │  Task Worker 2   │        │  Task Worker N   │
         │ (task_worker.py) │ │ (task_worker.py) │        │ (task_worker.py) │
         └──────────────────┘ ┌──────────────────┘        └──────────────────┘
                   │          │                                     │
                   ▼          ▼                                     ▼
         ┌──────────────────┐┌──────────────────┐        ┌──────────────────┐
         │  External APIs   ││  External APIs   │        │  External APIs   │
         │ (OpenAI,HeyGen,  ││ (OpenAI,HeyGen,  │        │ (OpenAI,HeyGen,  │
         │  ElevenLabs)     ││  ElevenLabs)     │        │  ElevenLabs)     │
         └──────────────────┘└──────────────────┘        └──────────────────┘
```

## Component Descriptions

**API Server** (`server.py`): Handles all HTTP requests, user interactions, and task queuing
**Master Worker** (`master_worker.py`): Polls Redis for tasks and dispatches to worker processes
**Task Workers** (`task_worker.py`): Process individual video generation tasks in isolation

## Data Flow

1. **User Interaction**: Users interact with the React web client to upload presentations
2. **Task Creation**: The API server creates processing tasks and queues them in Redis
3. **Task Distribution**: The master worker polls Redis for new tasks and spawns worker processes
4. **Parallel Processing**: Multiple worker processes handle tasks concurrently
5. **External API Integration**: Workers call various AI services (OpenAI, HeyGen, ElevenLabs)
6. **Result Storage**: Completed videos are stored in the output directory
7. **Status Updates**: Progress is tracked through Redis and made available via API endpoints

## Scalability Features

- **Horizontal Scaling**: Multiple worker processes can run on the same machine or across multiple machines
- **Load Distribution**: Redis queue ensures even distribution of tasks across available workers
- **Fault Tolerance**: Individual worker failures don't affect the entire system
- **Resource Isolation**: Each worker process runs in isolation, preventing resource contention

## Task Cancellation

The architecture supports immediate task cancellation through:
- Dedicated Redis keys for fast cancellation detection
- Periodic checkpoints in long-running operations
- Worker-level monitoring for quick response to cancellation requests
- Proper resource cleanup when tasks are cancelled

## Memory-Optimized Video Processing

Recent improvements to the video composition system address memory exhaustion issues when processing AI avatar videos:

### Memory Management Features
- **Per-slide processing**: Videos are processed one slide at a time to prevent memory exhaustion
- **Video validation**: Avatar videos are validated for corruption before processing
- **Resource cleanup**: Automatic cleanup of video clips and garbage collection after each slide
- **Memory-safe scaling**: Automatic dimension adjustment based on available memory
- **30-minute timeout**: Protection against hanging processes with automatic timeout
- **Optimized encoding**: Reduced memory usage with optimized video encoding settings

### Processing Flow
1. **Validation Phase**: All avatar videos are validated for corruption and compatibility
2. **Memory Planning**: Dimensions are calculated based on available system memory
3. **Sequential Processing**: Each slide is processed individually to manage memory
4. **Resource Management**: Automatic cleanup between slides prevents memory leaks
5. **Fallback Handling**: Graceful degradation if individual slides fail processing

### Error Handling
- **Corrupted video detection**: Early detection and handling of corrupted avatar videos
- **Memory exhaustion prevention**: Proactive memory management prevents system crashes
- **Timeout protection**: Automatic termination of hanging processes
- **Progress logging**: Real-time feedback during video composition