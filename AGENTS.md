# Repository Guidelines

## Project Structure & Module Organization
- `api/`: FastAPI backend (`slidespeaker/` modules, `routes/`, `processing/`, `pipeline/steps/`).
- `web/`: React + TypeScript frontend (`src/`, `public/`).
- `docs/`: Installation and API references.
- Supporting files: `api/Makefile`, `web/Makefile`.

## Build, Test, and Development Commands
- API: `cd api`
  - `make install`: Sync Python deps via `uv` (3.12).
  - `make dev` | `make start`: Run FastAPI (reload | prod).
  - `make lint` | `make format`: Ruff lint/format.
  - `make typecheck` | `make check`: mypy and combined checks.
- Web: `cd web`
  - `make install`: Install with `pnpm` if available, else `npm`.
  - `make dev` | `make build`: Start CRA dev server | build production.
  - `make lint` | `make lint-fix`: ESLint check/fix.
  - `make typecheck` | `make check`: TypeScript and combined checks.

## Coding Style & Naming Conventions
- Python: 4-space indent, 120-char lines (Ruff), type annotations enforced by mypy.
  - Names: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- Web (TS/React): ESLint (`react-app`), TypeScript `tsconfig.json`.
  - Names: components `PascalCase` in `src/components/`, files `.tsx`; styles `.scss` matching component name.

## Testing Guidelines
- Web: `npm test` (Jest + React Testing Library). Place tests near code as `*.test.tsx` or `*.test.ts`.
- API: No test suite committed yet; prioritize `make check`. If adding tests, use `pytest` under `api/tests/` with `test_*.py`.

## Commit & Pull Request Guidelines
- Commits: Prefer Conventional Commits (e.g., `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`, `build:`). Use imperative, concise subjects.
- PRs: Include summary, linked issues, screenshots for UI changes, and notes on breaking changes. Ensure `api make check` and `web make check` pass.

## Security & Configuration Tips
- API requires `.env` (OpenAI, Qwen, ElevenLabs, HeyGen, Redis). Never commit secrets.
- Engines: Python ≥3.12 via `uv`; Node ≥20 for web.

