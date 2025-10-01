# CLAUDE.md

Guidance for Claude Code when working in this repository. For general agent rules and UI/API specifics, also read AGENTS.md.

## Quick Start

### API (FastAPI)
```bash
cd api
make install           # Install deps via uv (Python 3.12)
make dev               # Run FastAPI in reload mode (port 8000)
make start             # Run FastAPI in prod mode
make master-worker     # Run master that spawns workers
make lint              # Ruff lint
make format            # Ruff format
make typecheck         # mypy type check
make check             # lint + typecheck
```

Optional uv variants:
```bash
uv sync                        # base deps
uv sync --extra=dev            # + dev tools
uv sync --extra=aws --extra=oss  # S3/OSS providers
```

### Web (React)
```bash
cd web
make install         # Prefer pnpm, fallback to npm
make dev             # Start dev server (port 3000)
make build           # Production build
make lint            # ESLint
make typecheck       # TypeScript
make check           # Lint + TS
```

## Repository Structure
- api/: FastAPI backend and workers
  - Entrypoints: server.py, master_worker.py, worker.py
  - Core: slidespeaker/core/ (state + queue)
  - Routes: slidespeaker/routes/ (upload, tasks, stats, downloads, transcripts)
  - Pipeline: slidespeaker/pipeline/ (PDF vs slides coordinators and steps)
  - Processing: slidespeaker/processing/ (audio/video/subtitles/images)
  - Services: slidespeaker/services/ (OpenAI, ElevenLabs, HeyGen, vision, TTS)
  - LLM: slidespeaker/llm/ (centralized OpenAI client + chat/image/tts helpers)
  - Storage: slidespeaker/storage/ (local, S3, OSS via unified interface)
- web/: React + TypeScript UI
  - Entrypoints: src/index.tsx, src/App.tsx
  - Components: src/components/ (TaskMonitor, TaskCard, PreviewModal, UploadPanel, ProcessingView, AudioPlayer, VideoPlayer, PodcastPlayer, TranscriptList)
  - Services: src/services/client.ts (API calls), src/services/queries.ts (React Query hooks + prefetch)
  - Types: src/types/ (Task, TaskState)
  - Styles: src/styles/ (index.scss, app.scss, TaskMonitor.scss, dark-theme.scss)

## Core Concepts
- task_type: What we are generating. Allowed: video | podcast | both. Drives whether video, podcast, or both artifacts are produced.
- source_type: Input source kind. Allowed: pdf | slides. Enforced end‑to‑end (upload → worker → coordinator). Hard error if missing/invalid.
- Task/ID mapping (Redis):
  - ss:task2file:{task_id} → {file_id}
  - ss:file2task:{file_id} → {task_id}
- Filenames: Prefer task‑id‑based filenames (e.g., {task_id}.mp4, {task_id}_{locale}.vtt|srt) when task_id exists.
- Subtitle Language Rule: Always use subtitle_language for subtitles and podcast transcript language. Never reuse voice_language for subtitle content.

## Backend Guidelines
- Use helpers in slidespeaker/llm (get_openai_client, chat_completion, image_generate, tts_speech_stream). Do not create raw OpenAI clients in modules.
- Coordinator requires valid source_type and branches PDF vs slides accordingly. Worker only overrides generation flags when task_type explicitly provided.
- Podcast pipeline:
  - Persist transcript language via subtitle_language for podcast tasks.
  - Include translate_podcast_script step when transcript_language != english.
  - Audio generation uses voice_language; transcript language is subtitle_language. Dialogues are translated accordingly before TTS when needed.
  - Remove any “Transition:” labels from dialogue when building/translating scripts and when rendering markdown.
  - Do not upload per‑segment MP3s to storage for PDF podcast; only upload the final composition.
- Migration: migrations/versions/0004_add_source_type_to_tasks.py adds tasks.source_type and backfills from kwargs.file_ext. Use alembic/uv via Makefile.
- Validation: run make check before pushing changes. Keep changes minimal and scoped; avoid unrelated fixes.

## Frontend Guidelines
- All API calls go through src/services/client.ts. Prefer React Query hooks in src/services/queries.ts for cache‑first UX.
- Reusable media/transcript components:
  - AudioPlayer: loads audio, parses VTT to cues, auto‑scroll/highlight, click‑to‑seek; width fits container/modal.
  - VideoPlayer: video with optional <track> for subtitles; consistent styling.
  - PodcastPlayer: audio + markdown transcript rendering.
  - TranscriptList: shared cue/timestamp list with active highlight and auto‑scroll.
- Views:
  - UploadPanel: upload box; “AUDIO LANGUAGE” and “Subtitles Language” labels; hide upload UI during upload/processing; Create button only when idle/ready.
  - ProcessingView: task meta in two equal‑width cards; correct badges; small preview where applicable.
  - TaskMonitor: task list + TaskCard per task. Preview modal closes on ESC and is sized larger for audio/podcast.
- UX rules (see AGENTS.md for full spec):
  - Downloads order: Video, Audio, Transcript, VTT, SRT.
  - Use task‑based URLs only: /api/tasks/{task_id}/...
  - Subtitles styling and rendering must match between preview and completed views.
  - Task card header: “Task: {task_id}”; task‑id label is focusable and click/Enter‑to‑copy.

## Environment & Config
Create api/.env (never commit secrets):
```
OPENAI_API_KEY=...
OPENAI_BASE_URL=             # optional; OpenAI‑compatible servers
ELEVENLABS_API_KEY=...
HEYGEN_API_KEY=...

STORAGE_PROVIDER=local       # local|s3|oss
# S3
AWS_S3_BUCKET_NAME=...
AWS_REGION=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
# OSS
OSS_BUCKET_NAME=...
OSS_ENDPOINT=...
OSS_ACCESS_KEY_ID=...
OSS_ACCESS_KEY_SECRET=...
OSS_REGION=...
```

## Development Workflow
1) Start API: `cd api && make dev` → http://localhost:8000/docs
2) Start Web: `cd web && make dev` → http://localhost:3000
3) Run workers for background processing: `cd api && make master-worker`
4) Validate: `make check` in both api/ and web/

## Do / Don’t
- Do use services/client.ts and services/queries.ts; avoid direct fetch/axios in components.
- Do follow types in src/types (Task/TaskState) for consistency.
- Do keep patches focused; prefer small utilities over inlined complex logic.
- Do preserve legacy backend endpoints, but frontend must use task‑based endpoints only.
- Don’t commit secrets, node_modules, or virtualenvs.
- Don’t change filenames/exports casually, or Makefile targets, unless requested.

## Agent Workflow (mirror of AGENTS.md)
- Plan: Use the built‑in plan tool (update_plan) for multi‑step work; keep 4–6 short steps; exactly one in_progress.
- Preambles: Before shell or patch calls, send a one‑sentence note of what’s next.
- Edits: Use apply_patch for file changes; keep changes minimal and scoped.
- Reads: Prefer rg for search; read files in ≤250‑line chunks.
- Validation: Run make check in api/ and web/ when appropriate; avoid unrelated fixes.
- Approvals/Sandbox: Default is workspace‑write FS, restricted network, approvals on‑request. Avoid destructive commands; don’t commit.

## Coding Conventions (mirror of AGENTS.md)
- Python: 4‑space indent; Ruff 120‑char lines; full type annotations; naming: snake_case for funcs/modules, PascalCase for classes, UPPER_SNAKE_CASE for constants.
- Web (TS/React): ESLint + tsconfig; components in src/components/ with PascalCase and matching .scss; keep functions small and typed.
- LLM: Use helpers in slidespeaker/llm (chat_completion, image_generate, tts_speech_stream); do not instantiate OpenAI clients directly.
- Scope: Keep patches tight; do not alter project structure/Make targets unless asked.

## Frontend UX Rules (Task Monitor & Redirect)
- Downloads order: Video, Audio, Transcript, VTT, SRT.
- “More” toggle at end of task details expands/collapses full download block (link‑style UI acceptable or native details/summary).
- Task‑based URLs only; never emit file‑based URLs in new UI.
- Subtitle styling/rendering unified between preview modal and task detail tabs.
- Remove file ID chip; keep header “Task: {task_id}”; task‑id label is focusable and copyable (Enter).
- Post-completion flow: show the redirect spinner copy (`completed.redirecting`) and push to `/[locale]/tasks/{id}`.
- Default font: Google Open Sans across the app.
- Status pills (Completed/Processing/Queued/Failed/Cancelled) follow theme colors with hover/focus.
- Processing Task Meta: two equal‑width cards; file icon/name don’t overlap; file‑type badge vertically centered.

## Testing & Verification (mirror of AGENTS.md)
- API: No formal tests; prioritize make check (Ruff + mypy). Place any new tests under api/tests/ as test_*.py.
- Web: If tests added, use Jest/RTL; keep tests near code (*.test.tsx|ts).
- Manual checks:
  - Start API (make dev) and verify /docs loads.
  - Start Web (make dev) and confirm Task Monitor fetches /api/tasks and uses task‑based endpoints:
    - /api/tasks/{task_id}/video
    - /api/tasks/{task_id}/audio
    - /api/tasks/{task_id}/transcripts/markdown
    - /api/tasks/{task_id}/subtitles/vtt|srt

## Security & Configuration (mirror of AGENTS.md)
- Secrets: Require api/.env (OpenAI, ElevenLabs, HeyGen, Redis). Never commit secrets. See api/.env.example.
- LLM config: OPENAI_API_KEY required; optional OPENAI_BASE_URL for compatible services; supports OPENAI_TIMEOUT/RETRIES/BACKOFF.
- Storage: STORAGE_PROVIDER (local|s3|oss) + related keys. Local mounts /files for direct serving.
- Engines: Python ≥3.12 via uv; Node ≥20 for web.

## Useful Entry Points (mirror of AGENTS.md)
- API server: api/server.py
- Master/Worker: api/master_worker.py, api/worker.py
- Queue/State: api/slidespeaker/core/task_queue.py, api/slidespeaker/core/state_manager.py
- Downloads (video/subtitles): api/slidespeaker/routes/downloads.py
- Transcripts (markdown): api/slidespeaker/routes/transcripts.py
- Task stats/search: api/slidespeaker/routes/stats.py
- Frontend monitor: web/src/components/TaskMonitor.tsx

## Known Gaps & Opportunities (mirror of AGENTS.md)
- API tests are absent; adding a minimal pytest scaffold later could help.
- TaskMonitor.tsx is large; we are actively refactoring into smaller components.
- Consider extracting shared locale maps/utilities to keep UI and API aligned.

## Troubleshooting Notes
- If you see duplicate type errors like “Identifier 'Cue' has already been declared”, ensure shared types live once at the component scope (use TranscriptList types) and remove duplicates.
- If subtitles don’t render, verify VTT fetch via services/queries useVttQuery and that components receive vttUrl or parsed cues. Ensure unified styling via styles/.
- If styles don’t apply, check that index.tsx imports `src/styles/index.scss` and App.tsx imports `src/styles/app.scss` and the dark theme overrides (`dark-theme.scss`). Task monitor styles live in `src/styles/TaskMonitor.scss`.
- If too many /api/tasks calls occur, ensure React Query keys are consistent and refetchInterval only runs when active tasks are on the current page.

## Recent Backend/Frontend Alignments
- Enforced source_type across upload/worker/coordinator with hard errors on invalid input.
- Podcast transcript language persists in subtitle_language; translation step appears when languages differ.
- Centralized audio generation language logic under slidespeaker/audio/generator.py; removed “Transition:” labels.
- Frontend uses reusable Audio/Video/Podcast players and TranscriptList to unify subtitles/transcripts across preview and completed views.

-- do NOT git commit
-- do NOT check the node_modules and .venv
- always use uv for python, pnpm for frontend
