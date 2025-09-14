# SlideSpeaker

Turn slides/PDFs into narrated videos — transcripts, TTS, subtitles, and optional avatars.

## Quick Start

- API
  - `cd api`
  - `uv sync` (add `--extra=dev|aws|oss` as needed)
  - Copy `api/.env.example` → `api/.env` and set `OPENAI_API_KEY`
  - `make dev`
- Web
  - `cd web`
  - `pnpm install` (or `npm install`)
  - `pnpm start` (or `npm start`)

Visit `http://localhost:3000` (UI) and `http://localhost:8000/docs` (API docs).

## Config (essentials)

- LLM (OpenAI)
  - `OPENAI_API_KEY` (required)
  - Optional: `OPENAI_BASE_URL` (for OpenAI‑compatible endpoints)
  - Optional: `OPENAI_TIMEOUT`, `OPENAI_RETRIES`, `OPENAI_BACKOFF`
- TTS
  - `TTS_SERVICE=openai|elevenlabs` (invalid values fall back to `openai`)
  - ElevenLabs requires `ELEVENLABS_API_KEY`
- Storage
  - Defaults to local. To use S3/OSS, set the corresponding envs in `.env`.

## What it does

- Generates slide/section scripts with OpenAI (with optional revision)
- Produces audio via OpenAI TTS or ElevenLabs
- Builds subtitles in the selected language
- Composes a final video (avatars optional)
- Provides task‑based downloads for video, audio, transcripts, and subtitles

## Endpoints (task‑based)

- `/api/tasks/{task_id}/video`
- `/api/tasks/{task_id}/audio`
- `/api/tasks/{task_id}/transcripts/markdown`
- `/api/tasks/{task_id}/subtitles/vtt|srt`

More in [docs/installation.md](docs/installation.md) and [docs/api.md](docs/api.md).

## License

MIT

