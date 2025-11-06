# Repository Guidelines

## Project Structure & Module Organization
- `slidespeaker/` holds the application code, grouped by domain (e.g., `audio/`, `document/`, `llm/`, `routes/`, `storage/`). Use existing package boundaries when adding features.
- `server.py` bootstraps the FastAPI app; `master_worker.py` manages background workers; `cli.py` exposes maintenance utilities.
- `tests/` mirrors the package layout. Place new tests alongside the module under test.
- `alembic/` and `migrations/` track database schema changes; `scripts/` contains operational helpers; `docs/` stores higher-level reference material (organized in subdirectories: `getting-started/`, `api/`, `architecture/`).

## Build, Test, and Development Commands
- `make install` / `make install_dev` sync dependencies via `uv sync` (add `--extra=oss`/`aws` as needed).
- `make api` runs the FastAPI development server with auto-reload; `make start` launches the production variant.
- `make worker` starts the master worker loop; `make cli` surfaces CLI options for batch jobs.
- `make lint`, `make format`, and `make check` run Ruff (formatter + linter) and the strict mypy gate.
- `make test` executes the pytest suite; `make test-cov` adds coverage details.

## Coding Style & Naming Conventions
- Python code follows Ruff rules (line length 120, double-quoted strings, space indentation). Run `make format` before opening a PR.
- Keep modules and functions snake_case, classes PascalCase, and constants UPPER_SNAKE_CASE. Mirror existing package naming when adding submodules.
- Mypy runs in strict mode; annotate new functions, dataclasses, and async entry points. Prefer explicit return types for FastAPI route handlers and background tasks.

## Documentation Structure
- Documentation has been reorganized into logical subdirectories:
  - `docs/getting-started/` - Installation and setup guides
  - `docs/api/` - API documentation (overview and reference)
  - `docs/architecture/` - System architecture and data flow docs
- Update the appropriate subdirectory when adding new documentation
- Update the main `docs/README.md` to reflect any new documentation files

## Testing Guidelines
- Pytest with `pytest-asyncio` powers the async tests. Name files `test_*.py`, classes `Test*`, and functions `test_*` to honour `pyproject.toml`.
- Exercise both successful and failure paths for background jobs, storage integrations, and API routes. Use `tests/fixtures` patterns for reusable setup.
- Target `make test-cov` before merging; expand coverage for new modules to keep the report green.

## Commit & Pull Request Guidelines
- Follow the existing short, typed messages (`feat:`, `refactor:`, `fix:`, `chore:`). Use imperative mood and keep the subject under ~72 characters.
- Each commit should remain logically scoped (API change, migration, chore). Update migrations and fixtures in the same commit as the code they support.
- Pull requests must describe intent, outline testing performed, and link related issues. Attach logs or API samples when changing service endpoints or worker flows.
- Request review once `make check` and `make test` pass locally; flag breaking changes or ops steps (Alembic upgrades, storage backfills) in the PR.

## Environment & Configuration Tips
- Store secrets in `.env` files referenced by `slidespeaker/configs`; never commit credentials. Document new keys in `README.md` or `docs/`.
- Use Alembic (`make db-migrate[-named]`) for schema changes and `scripts/storage_backfill` for data rewrites; coordinate with the ops team before running destructive commands.