# SlideSpeaker Documentation

Welcome to the SlideSpeaker documentation. This directory contains comprehensive guides and references for understanding and working with the SlideSpeaker platform.

## Table of Contents

### Getting Started
- [Installation Guide](getting-started/installation.md) - Prerequisites and setup instructions

### API Documentation
- [API Overview](api/api-overview.md) - High-level overview of the API architecture
- [API Reference](api/api-reference.md) - Complete API reference and endpoints

### Architecture
- [Pipeline Overview](architecture/pipeline-overview.md) - High-level processing pipeline architecture
- [Step Definitions](architecture/step-definitions.md) - Detailed breakdown of processing steps
- [Data Flow](architecture/dataflow.md) - Data flow and state management

## Architecture Overview

SlideSpeaker follows a modern microservices architecture with clear separation of concerns:

### Frontend (web/)
- **Framework**: React 18 with Next.js App Router
- **Language**: TypeScript
- **State Management**: Zustand (local) + React Query (server)
- **Styling**: Sass/SCSS with CSS Modules
- **Internationalization**: next-intl with multi-language support

### Backend (api/)
- **Framework**: FastAPI (Python 3.12+)
- **Task Queue**: Redis-based asynchronous processing
- **Architecture**: Master-worker pattern for scalable processing
- **Storage**: Unified interface supporting local filesystem, AWS S3, and Aliyun OSS

### Key Integrations
- **AI Services**: OpenAI (primary), ElevenLabs (TTS), HeyGen (avatars)
- **Media Processing**: FFmpeg, MoviePy, Pillow
- **Authentication**: JWT-based session management
- **Monitoring**: Built-in metrics and health checks

## Development Guidelines

### Frontend Development
1. Use TypeScript for all new components
2. Follow component-based architecture patterns
3. Leverage Zustand stores for local state management
4. Use React Query for server state and data fetching
5. Maintain WCAG 2.1 AA accessibility compliance
6. Support all configured internationalization locales

### Backend Development
1. Use FastAPI's type hints and Pydantic models
2. Follow the master-worker architecture for processing tasks
3. Implement proper error handling and logging
4. Use the unified storage interface for file operations
5. Maintain API documentation with OpenAPI annotations
6. Implement rate limiting for public endpoints

## API Documentation

The backend API is documented through OpenAPI/Swagger:
- **Local Development**: http://localhost:8000/docs
- **Production**: https://your-domain.com/api/docs

## Deployment

### Local Development
- **Frontend**: `cd web && pnpm dev`
- **Backend**: `cd api && make dev`
- **Workers**: `cd api && make master-worker`

### Production Deployment
- Docker containerization support
- Kubernetes deployment configurations
- Cloud provider specific deployment guides
- Monitoring and alerting setup

## Contributing

Please refer to the project's main README.md and the AGENTS.md guide for contribution guidelines and development workflows.

## Support

For questions or issues, please check the existing documentation or open an issue in the repository.