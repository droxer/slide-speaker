# Repository Guidelines

This guide helps contributors work productively across the FastAPI backend and the React web app. Keep changes focused, follow the conventions below, and prefer existing patterns.

## Project Structure & Modules
- Backend: `api/` (FastAPI + workers). Entrypoints: `api/server.py`, `api/master_worker.py`, `api/worker.py`.
- Core modules: `api/slidespeaker/{core,configs,routes,pipeline,processing,services,llm,storage}/`.
- Frontend: `web/` (React + TypeScript). Main app: `web/src/App.tsx`; monitor: `web/src/components/TaskMonitor.tsx`.
- Docs: `docs/`; Top-level: `README.md`, `CLAUDE.md`.

## Build, Test, and Development
- API (`cd api`): `make install` (deps via uv), `make dev` (reload), `make start` (prod), `make lint`/`make format` (Ruff), `make typecheck`/`make check` (mypy + all), `make master-worker` (spawn workers).
- Web (`cd web`): `make install` (pnpm preferred, npm fallback), `make dev` (Vite dev), `make build` (production), `make lint`/`make lint-fix` (ESLint), `make typecheck`/`make check` (TS + all).

## Coding Style & Naming
- Python: 4 spaces, Ruff 120‑col, full type hints. Names: functions/modules `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- TS/React: ESLint + `tsconfig.json`. Components `PascalCase` in `web/src/components/` with matching `.scss`.
- Use `slidespeaker/llm` helpers for OpenAI/voice/vision instead of creating clients directly.

## Testing Guidelines
- API: No formal tests yet; run `make check`. If adding tests, place under `api/tests/` as `test_*.py`.
- Web: Jest + React Testing Library via `npm test` (or `pnpm test`). Keep tests near code: `*.test.tsx|ts`.

## Commit & Pull Requests
- Commits: Short, imperative subject; scope where useful (e.g., `api: fix retry backoff`). Group related changes only.
- PRs: Clear description, linked issues, reproduction steps. Include screenshots for UI changes. Note breaking changes and migration steps.

## Security & Configuration
- Secrets live in `api/.env` (see `api/.env.example`). Never commit secrets. Required: `OPENAI_API_KEY`; optional: `OPENAI_BASE_URL`, timeouts/retries.
- Storage: set `STORAGE_PROVIDER` (`local|s3|oss`) and keys. Local mounts `/files` for direct serving.
- Engines: Python ≥ 3.12 (uv), Node ≥ 20.

## Architecture Notes
- Prefer task‑based endpoints (e.g., `/api/tasks/{task_id}/video|audio|transcripts/markdown|subtitles/{vtt|srt}`) from the frontend.
- Generated assets should use task‑id filenames where possible.
