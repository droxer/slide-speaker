# Repository Guidelines

This guide helps contributors work productively across the FastAPI backend and the React web app. Keep changes focused, follow the conventions below, and prefer existing patterns.

## Project Structure & Modules
- Backend: `api/` (FastAPI + workers). Entrypoints: `api/server.py`, `api/master_worker.py`, `api/worker.py`.
- Core modules: `api/slidespeaker/{core,configs,routes,pipeline,processing,services,llm,storage}/`.
- Frontend: `web/` (Next.js + React + TypeScript). Main client surface: `web/src/App.tsx`; creation monitor: `web/src/components/TaskMonitor.tsx`.
- App Router: locale-aware routes live under `web/src/app/[locale]/`. Shared client entry points sit in `web/src/app/*PageClient.tsx`. Use the non-locale directories only for server components that seed data before delegating to the client versions.
- Internationalization: `web/src/i18n/` holds `config.ts`, message catalogs, and hooks. Navigation helpers live in `web/src/navigation.ts`. Middleware (`web/middleware.ts`) wires next-intl locale detection.
- UI components: `web/src/components/` (match `.scss` files). `LanguageSwitcher` handles locale changes inside detail views. Download surfaces live in `DownloadLinks`.
- Docs: `docs/`; Top-level: `README.md`, `CLAUDE.md`, `QWEN.md`.

## Build, Test, and Development
- API (`cd api`): `make install` (deps via uv), `make dev` (reload), `make start` (prod), `make lint`/`make format` (Ruff), `make typecheck`/`make check` (mypy + all), `make master-worker` (spawn workers).
- Web (`cd web`): `make install` (pnpm preferred, npm fallback), `make dev` (Next dev server), `make build` (production), `make lint`/`make lint-fix` (ESLint), `make typecheck`/`make check` (TS + all).

## Coding Style & Naming
- Python: 4 spaces, Ruff 120-col, full type hints. Names: functions/modules `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- TS/React: follow ESLint + `tsconfig.json`. Components `PascalCase` in `web/src/components/` with matching `.scss`.
- I18n: inside React components or hooks call `useI18n()` from `web/src/i18n/hooks`. Provide a sensible fallback string (third argument) for any `t()` call that might miss a translation.
- Use `slidespeaker/llm` helpers for OpenAI/voice/vision instead of creating clients directly.

## Internationalization Workflow
- Locales currently ship with `en`, `zh-CN`, `zh-TW`. Add new keys to every catalog in `web/src/i18n/messages/`.
- Shared navigation helpers (`web/src/navigation.ts`) and middleware rely on `defaultLocale` from `config.ts`; update both when introducing locales.
- Surface locale controls via `LanguageSwitcher` where users need to swap languages.

## Testing Guidelines
- API: No formal tests yet; run `make check`. If adding tests, place under `api/tests/` as `test_*.py`.
- Web: Jest + React Testing Library via `npm test` (or `pnpm test`). Keep tests near code: `*.test.tsx|ts`.
- Manual verification: when touching Creations trash logic or task routing, confirm the task disappears immediately and redirects land on `/[locale]/tasks/{id}` without relying on the removed Completed view.

## Commit & Pull Requests
- Commits: Short, imperative subject; scope where useful (e.g., `api: fix retry backoff`). Group related changes only.
- PRs: Clear description, linked issues, reproduction steps. Include screenshots for UI changes. Note breaking changes and migration steps.

## Security & Configuration
- Secrets live in `api/.env` (see `api/.env.example`). Never commit secrets. Required: `OPENAI_API_KEY`; optional: `OPENAI_BASE_URL`, timeouts/retries.
- Storage: set `STORAGE_PROVIDER` (`local|s3|oss`) and keys. Local mounts `/files` for direct serving.
- Engines: Python ≥ 3.12 (uv), Node ≥ 20.

## Architecture Notes
- Upload flow no longer stores transient state in `localStorage`; rely on React Query cache and component state.
- Completed processing skips the old Completed view; we show a short spinner then navigate straight to the task detail page. Keep redirects in sync with `/[locale]/tasks/[taskId]/page.tsx`.
- Creations trash actions cancel active tasks and purge completed ones; update cached lists so cards disappear immediately before awaiting server confirmation.
- Prefer task-based endpoints (e.g., `/api/tasks/{task_id}/video|audio|transcripts/markdown|subtitles/{vtt|srt}`) from the frontend.
- Generated assets should use task-id filenames where possible.
