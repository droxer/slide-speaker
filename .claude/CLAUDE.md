# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SlideSpeaker is an AI-powered system that converts slides/PDFs into narrated videos, podcasts, transcripts, and subtitles. The backend is built with Python/FastAPI and follows a microservices architecture with Redis for task queuing.

## Key Commands

### Development
- `make dev` - Start development server with auto-reload on port 8000
- `make master-worker` - Start master process that spawns worker processes
- `make cli` - Show CLI tool help for task management

### User Management
- `python scripts/user_cli.py list` - List all users
- `python scripts/user_cli.py create --email you@example.com --password secret --name "You"` - Create a new user
- `python scripts/user_cli.py --help` - See all user management options

### Testing
- `make test` - Run unit tests
- `make test-cov` - Run tests with coverage report

### Code Quality
- `make lint` - Run Ruff linter
- `make format` - Run Ruff formatter
- `make check` - Run both linting and type checking

### Database
- `make db-upgrade` - Alembic upgrade to head
- `make db-status` - Show current alembic revision and history

## Code Architecture

### Core Components

1. **API Server** (`server.py`) - FastAPI application with route registration
2. **Master Worker** (`master_worker.py`) - Manages task distribution to worker processes
3. **Task Workers** (`worker.py`) - Execute media processing pipelines
4. **CLI Tools** (`cli.py`, `scripts/user_cli.py`) - Command-line utilities

### Key Modules

- `slidespeaker/core/` - Task queue, state management, rate limiting
- `slidespeaker/routes/` - HTTP endpoints organized by functionality
- `slidespeaker/pipeline/` - Processing pipeline coordination
- `slidespeaker/repository/` - Database access layer
- `slidespeaker/storage/` - Storage abstraction layer
- `slidespeaker/configs/` - Configuration management

### Processing Pipeline

The system supports three main processing paths:
1. PDF to Video
2. PDF to Podcast
3. Slides (PPT/PPTX) to Video

Each pipeline uses a coordinator pattern with step-based execution and Redis state management.

## Configuration

Key environment variables in `.env`:
- `OPENAI_API_KEY` - Required for LLM services
- `STORAGE_PROVIDER` - local, s3, or oss
- `REDIS_HOST/PORT` - Redis connection
- `DATABASE_URL` - PostgreSQL connection

## Task Management

Tasks are managed through Redis with the following states:
- pending, processing, completed, failed, cancelled

Use the CLI tools to manage tasks:
- `python cli.py list-states` - List all task states
- `python cli.py get-task <task_id>` - Get task details
- `python cli.py cancel-task <task_id>` - Cancel a task
- `python cli.py delete-state <file_id>` - Delete task state