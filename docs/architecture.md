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