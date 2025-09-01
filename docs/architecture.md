# Architecture Overview

## System Architecture

SlideSpeaker follows a modular, service-oriented architecture with clear separation between frontend and backend components.

```
┌─────────────────┐    ┌──────────────────┐
│   Frontend      │    │    Backend       │
│   (React)       │◄──►│   (FastAPI)      │
└─────────────────┘    └──────────────────┘
                              │
                     ┌──────────────────┐
                     │   Redis (State)  │
                     └──────────────────┘
                              │
                   ┌───────────────────────┐
                   │  External Services    │
                   │  ┌─────────────────┐  │
                   │  │   OpenAI GPT    │  │
                   │  ├─────────────────┤  │
                   │  │  ElevenLabs     │  │
                   │  ├─────────────────┤  │
                   │  │    HeyGen       │  │
                   │  └─────────────────┘  │
                   └───────────────────────┘
```

## Backend Architecture

### Main Components

1. **Orchestrator** (`slidespeaker/orchestrator.py`)
   - Coordinates the entire presentation processing pipeline
   - Manages state transitions between processing steps
   - Handles error recovery and resume capability

2. **State Manager** (`slidespeaker/state_manager.py`)
   - Manages processing state using Redis
   - Tracks progress of each step
   - Stores intermediate results and error information

3. **Task Manager** (`slidespeaker/task_manager.py`)
   - Handles background task processing
   - Manages task queues and worker processes

4. **Slide Processor** (`slidespeaker/slide_processor.py`)
   - Extracts content from PDF and PowerPoint files
   - Converts slides to images for processing

5. **Script Generator** (`slidespeaker/script_generator.py`)
   - Uses OpenAI GPT to generate presentation scripts
   - Supports multiple languages

6. **Script Reviewer** (`slidespeaker/orchestrator.py`)
   - Reviews and refines generated scripts for consistency
   - Ensures smooth transitions between slides

7. **TTS Service** (`slidespeaker/tts_service.py`)
   - Generates audio from text using OpenAI or ElevenLabs
   - Handles multiple languages and voices

8. **Avatar Service** (`slidespeaker/avatar_service_unified.py`)
   - Generates AI avatar videos using HeyGen
   - Includes fallback to alternative implementation

9. **Vision Service** (`slidespeaker/vision_service.py`)
   - Analyzes slide images for contextual understanding
   - Enhances script generation with visual context

10. **Video Composer** (`slidespeaker/video_composer.py`)
    - Combines slides, audio, and avatar videos
    - Uses FFmpeg for video processing

### Processing Pipeline

The backend follows an 8-step processing pipeline:

1. **Extract Slides** - Parse presentation file and extract content
2. **Convert to Images** - Render slides as images for processing
3. **Analyze Images** - Use AI to understand visual content
4. **Generate Scripts** - Create AI narratives for each slide
5. **Review Scripts** - Refine scripts for consistency and flow
6. **Generate Audio** - Create text-to-speech audio files
7. **Generate Avatars** - Create AI avatar videos
8. **Compose Video** - Combine all elements into final presentation

### State Management

The system uses Redis to maintain processing state, enabling:
- Resume capability after interruptions
- Progress tracking and monitoring
- Concurrent processing of multiple presentations
- Error recovery and retry mechanisms

## Frontend Architecture

### Main Components

1. **App Component** (`src/App.js`)
   - Main application interface
   - File upload and progress tracking
   - Video preview and download

2. **State Management**
   - React hooks for local state management
   - Real-time updates via API polling
   - Progress visualization

### User Flow

1. **Upload** - User selects and uploads presentation file
2. **Processing** - Real-time progress tracking during AI processing
3. **Review** - View completed video and error details
4. **Download** - Download final video presentation

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.12+)
- **AI Services**: OpenAI GPT, ElevenLabs, HeyGen
- **Processing**: FFmpeg, MoviePy
- **Storage**: Redis
- **Documents**: PyPDF2, python-pptx
- **Dependencies**: Managed with uv/pip

### Frontend
- **Framework**: React
- **State Management**: React Hooks
- **Styling**: CSS Modules
- **API Communication**: Axios
- **Build Tool**: Create React App
- **Dependencies**: Managed with npm/pnpm

## Data Flow

1. User uploads presentation file
2. Backend stores file and creates processing state
3. Background task queue processes presentation through 8 steps
4. Each step updates state in Redis
5. Frontend polls for progress updates
6. Final video is composed and stored
7. User downloads completed video