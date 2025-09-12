# AGENTS.md

Guidance for AI coding agents (Codex CLI, Claude Code, etc.) collaborating on this repository.

## Quick Start Commands
- API (`cd api`):
  - `make install`: Install deps via `uv` (Python 3.12).
  - `make dev` | `make start`: Run FastAPI in reload | prod mode.
  - `make lint` | `make format`: Ruff lint/format.
  - `make typecheck` | `make check`: mypy or combined checks.
  - `make master-worker`: Run master process that spawns workers.
- Web (`cd web`):
  - `make install`: Prefer `pnpm`, fallback to `npm`.
  - `make dev` | `make build`: Start dev server | build production.
  - `make lint` | `make lint-fix`: ESLint check/fix.
  - `make typecheck` | `make check`: TS or combined checks.

## Repository Structure
- `api/`: FastAPI backend and workers
  - Entrypoints: `server.py`, `master_worker.py`, `worker.py`.
- Core: `slidespeaker/core/` (state + queue), `slidespeaker/configs/` (config, Redis, logging).
  - Routes: `slidespeaker/routes/` (upload, tasks, stats, downloads, languages).
  - Pipeline: `slidespeaker/pipeline/` (PDF vs slides coordinators and steps).
  - Processing: `slidespeaker/processing/` (audio/video/subtitles/images).
  - Services: `slidespeaker/services/` (OpenAI, Qwen, ElevenLabs, HeyGen, vision, TTS).
  - Storage: `slidespeaker/storage/` (local, S3, OSS via unified interface).
- `web/`: React + TypeScript UI
  - Entrypoints: `src/index.tsx`, `src/App.tsx`.
  - Main component: `src/components/TaskMonitor.tsx` (+ Sass styles).
  - Theme overrides: `src/styles/ultra-flat-overrides.scss`, `src/styles/subtle-material-overrides.scss`.
- `docs/`: Installation and API references.
- Top-level: `README.md`, `CLAUDE.md`, this `AGENTS.md`.

## Agent Workflow (Codex CLI)
- Plan: Use `update_plan` to outline steps for multi-part work. Keep 4–6 short steps; exactly one in progress.
- Preambles: Before shell or patch calls, add a one‑sentence note of what’s next.
- Edits: Use `apply_patch` to modify files. Keep changes minimal and scoped.
- Reads: Prefer `rg` for search and read files in ≤250‑line chunks.
- Validation: When appropriate, run `make check` in `api`/`web`. Avoid unrelated fixes.
- Approvals/Sandbox: Default mode is workspace‑write FS, restricted network, approvals on‑request. Avoid destructive commands; don’t commit.

## Coding Conventions
- Python: 4‑space indent; Ruff 120‑char lines; full type annotations; names: functions/modules `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- Web (TS/React): ESLint + `tsconfig.json`; components `PascalCase` in `src/components/` with matching `.scss`.
- Do: Follow existing patterns, keep functions small, add docstrings where present elsewhere.
- Don’t: Change filenames/exports casually, add license headers, or commit secrets.

## Frontend UX Rules (Task Monitor & Completed View)
- Downloads in task cards: show same options as completed view, ordered exactly: Video, Audio, Transcript, VTT, SRT.
- Use a link-style “More” toggle at the end of task details to expand/collapse the full download block.
- Task-based URLs only; do not emit file-based URLs in new UI.
- Subtitle styling and rendering must match between preview and completed views.
- Remove the file ID chip in task cards; keep the header “Task: {task_id}”. The task-id label is focusable and click/Enter-to-copy enabled.
- Completed headline text: “Your Masterpiece is Ready!”.
- Default font: Google Open Sans across the web app.
- Status pills (Completed/Processing/Queued/Failed/Cancelled) adopt theme colors in both Flat and Subtle‑Material themes with hover/focus states.

## Testing & Verification
- API: No formal tests yet. Prioritize `make check` (Ruff + mypy). If you add tests, place under `api/tests/` as `test_*.py`.
- Web: Use `npm test` (Jest + RTL) if tests are added. Keep tests near code as `*.test.tsx|ts`.
- Manual checks:
  - Start API (`make dev`) and ensure `/docs` loads.
  - Start Web (`make dev`) and verify Task Monitor fetches `/api/tasks` and uses task-based endpoints for resources:
    - `/api/tasks/{task_id}/video`
    - `/api/tasks/{task_id}/audio`
    - `/api/tasks/{task_id}/transcripts/markdown`
    - `/api/tasks/{task_id}/subtitles/vtt|srt`

## Security & Configuration
- Secrets: Require `api/.env` (OpenAI, Qwen, ElevenLabs, HeyGen, Redis). Never commit secrets. See `api/.env.example`.
- Storage: Configure `STORAGE_PROVIDER` (`local|s3|oss`) and related keys. Local mounts `/files` for direct serving.
- Engines: Python ≥ 3.12 via `uv`; Node ≥ 20 for web.

## Useful Entry Points
- API server: `api/server.py`
- Master/Worker: `api/master_worker.py`, `api/worker.py`
- Queue/State: `api/slidespeaker/core/task_queue.py`, `api/slidespeaker/core/state_manager.py`
- Downloads (video/subtitles): `api/slidespeaker/routes/downloads.py`
- Transcripts (markdown): `api/slidespeaker/routes/transcripts.py`
- Task stats/search: `api/slidespeaker/routes/stats.py`
- Frontend monitor: `web/src/components/TaskMonitor.tsx`

## Do/Don’t (for Agents)
- Do: Keep patches tight; explain rationale briefly in the PR description or final message.
- Do: Prefer adding small utility functions over inlining complex logic.
- Do: Preserve backend legacy endpoints for compatibility, but the frontend must use task-based endpoints only.
- Don’t: Introduce network‑dependent steps in CI without feature flags.
- Don’t: Alter Makefile targets or project structure unless requested.

## Known Gaps & Opportunities
- API tests are not present; adding a minimal `pytest` scaffold could help future changes.
- Frontend `TaskMonitor.tsx` is large; potential refactor into smaller components for readability.
- Consider extracting shared locale maps into a single source to keep UI/API aligned.

## Task/ID Mapping and Filenames
- Persist mappings on upload (Redis keys):
  - `ss:task2file:{task_id}` → `{file_id}` (TTL ~30 days)
  - `ss:file2task:{file_id}` → `{task_id}` (TTL ~30 days)
- Backend resolvers should prefer task → file mapping, with fallback to task payload only if mapping is absent.
- Generated assets prefer task-id-based filenames when `state.task_id` exists (e.g., `{task_id}.mp4`, `{task_id}_{locale}.vtt|srt`).

## Subtitle Language Rule
- Always use `subtitle_language` for subtitle generation and translation. Do not reuse `voice_language` for subtitle content.

## Repository Guidelines (Reference)
- Project structure, commands, styles, testing, commits/PRs, and security tips mirror the summary above. See also `README.md` and `CLAUDE.md` for architecture and deeper context.
