# Installation Guide

## Prerequisites

- Python 3.12+
- Node.js 16+
- Redis server
- FFmpeg
- API keys for:
  - OpenAI
  - ElevenLabs
  - HeyGen

## Backend Setup

1. Navigate to the API directory:
   ```bash
   cd api
   ```

2. Install Python dependencies:
   ```bash
   uv sync
   ```

3. Create a `.env` file in the `api/` directory:
   ```env
   OPENAI_API_KEY=your_openai_api_key
   ELEVENLABS_API_KEY=your_elevenlabs_api_key
   HEYGEN_API_KEY=your_heygen_api_key
   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_PASSWORD=your_redis_password_or_empty
   ```

4. Start Redis:
   ```bash
   # On macOS with Homebrew
   brew services start redis

   # Or using the provided Makefile
   make redis-start
   ```

5. Start the API server:
   ```bash
   # Using the Makefile
   make dev

   # Or directly
   uv run python main.py
   ```

## Frontend Setup

1. Navigate to the web directory:
   ```bash
   cd web
   ```

2. Install Node.js dependencies:
   ```bash
   npm install  # or pnpm install
   ```

3. Start the development server:
   ```bash
   npm start    # or pnpm start
   ```

The frontend will be available at `http://localhost:3000` and automatically proxy API requests to the backend at `http://localhost:8000`.