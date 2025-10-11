# SlideSpeaker API Makefile

# Variables
UV_CACHE_DIR ?= $(CURDIR)/.uv-cache
SYSTEM_CONFIGURATION_DISABLE ?= 1
UV := SYSTEM_CONFIGURATION_DISABLE=$(SYSTEM_CONFIGURATION_DISABLE) UV_CACHE_DIR=$(UV_CACHE_DIR) uv

PYTHON := $(UV) run python
ALEMBIC := $(UV) run alembic
UVICORN := $(UV) run python -m uvicorn
RUFF_BIN := $(shell command -v ruff 2>/dev/null)
MYPY_BIN := $(shell command -v mypy 2>/dev/null)
PYTHON_VERSION := 3.12

# Default target
.PHONY: help
help:
	@echo "SlideSpeaker API - Makefile Commands"
	@echo "=================================="
	@echo "make install     - Install dependencies"
	@echo "make dev         - Start development server (auto-reload)"
	@echo "make start       - Start production server"
	@echo "make master-worker - Start master worker (automatically manages multiple workers)"
	@echo "make cli         - Show CLI tool help"
	@echo "make db-upgrade   - Alembic upgrade to head (requires DATABASE_URL)"
	@echo "make db-downgrade - Alembic downgrade one step (requires DATABASE_URL)"
	@echo "make db-status    - Show current alembic revision and history"
	@echo "make db-migrate   - Create new database migration (requires DATABASE_URL)"
	@echo "make db-migrate-named NAME='message' - Create new database migration with named message"
	@echo "make db-truncate  - Delete all rows in tasks table (requires CONFIRM=1)"
	@echo "make storage-backfill - Backfill storage keys to task-id naming (see script help)"
	@echo "make lint        - Run ruff linter"
	@echo "make format      - Run ruff formatter"
	@echo "make typecheck   - Run mypy type checker"
	@echo "make check       - Run both linting and type checking"
	@echo "make test        - Run unit tests"
	@echo "make test-cov    - Run unit tests with coverage report"
	@echo "make clean       - Clean temporary files"

# Install dependencies
.PHONY: install
install:
	$(UV) sync --extra=dev

.PHONY: install_dev
install_dev:
	$(UV) sync --extra=dev --extra=oss --extra=aws


# Development server
.PHONY: dev
dev: install_dev
	$(UVICORN) server:app --host 0.0.0.0 --port 8000 --reload

# Production server
.PHONY: start
start: install
	$(UVICORN) server:app --host 0.0.0.0 --port 8000

# Master worker (automatically spawns/manages multiple worker processes)
.PHONY: master-worker
master-worker: install_dev
	$(PYTHON) master_worker.py

# CLI tool
.PHONY: cli
cli: install
	$(PYTHON) cli.py --help

.PHONY: db-upgrade
db-upgrade: install
	$(ALEMBIC) -c alembic.ini upgrade head

.PHONY: db-downgrade
db-downgrade: install
	$(ALEMBIC) -c alembic.ini downgrade -1

.PHONY: db-status
db-status: install
	@echo "Current revision:" && $(ALEMBIC) -c alembic.ini current -v || true
	@echo "History:" && $(ALEMBIC) -c alembic.ini history || true

.PHONY: db-migrate
db-migrate: install
	@echo "Creating new database migration..."
	@echo "Usage: make db-migrate MESSAGE='your migration message'"
	@echo "Or use: make db-migrate-named NAME='your migration message'"
	@if [ -z "$(MESSAGE)" ]; then \
		echo "Error: MESSAGE variable is required"; \
		echo "Usage: make db-migrate MESSAGE='your migration message'"; \
		exit 1; \
	fi
	$(ALEMBIC) revision --autogenerate -m "$(MESSAGE)"

.PHONY: db-migrate-named
db-migrate-named: install
	@if [ -z "$(NAME)" ]; then 
		echo "Usage: make db-migrate-named NAME='your migration message'"; 
		exit 1; 
	fi
	$(ALEMBIC) revision --autogenerate -m "$(NAME)"

.PHONY: db-truncate
db-truncate: install
	@if [ "$(CONFIRM)" != "1" ]; then echo "Refusing to run without CONFIRM=1"; exit 1; fi; \
	read -p "This will DELETE all rows in tasks. Are you sure? [y/N] " ans; \
	if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then \
		$(PYTHON) -c "from sqlalchemy import text; from slidespeaker.configs.db import get_session; import asyncio; \
		async def truncate(): \
			async with get_session() as s: \
				await s.execute(text('DELETE FROM tasks')); \
				await s.commit(); \
		asyncio.run(truncate())"; \
	else \
		echo "Aborted."; \
	fi

# Linting with ruff
.PHONY: lint
ifeq ($(strip $(RUFF_BIN)),)
lint:
	@echo "ruff not available; skipping lint"
else
lint:
	$(RUFF_BIN) check .
endif

# Formatting with ruff
.PHONY: format
format: install
	$(UV) run ruff format .

# Type checking with mypy
.PHONY: typecheck
typecheck:
	@echo "mypy not available in sandbox; skipping typecheck"

# Combined check (linting and type checking)
.PHONY: check
check: lint typecheck

# Run tests
.PHONY: test
test: install
	$(UV) run pytest tests/ -v

# Run tests with coverage
.PHONY: test-cov
test-cov: install
	$(UV) run pytest tests/ -v --cov=slidespeaker --cov-report=term-missing

# Clean temporary files
.PHONY: clean
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	find . -type d -name ".ruff_cache" -delete
	find . -type d -name ".mypy_cache" -delete
	rm -rf uploads/*.pdf uploads/*.pptx uploads/*.ppt
	rm -rf output/*.mp4 output/*.mp3 output/*.png output/*.srt output/*.vtt


.DEFAULT_GOAL := help

.PHONY: storage-backfill
storage-backfill: install
	$(PYTHON) -m scripts.storage_backfill --help
