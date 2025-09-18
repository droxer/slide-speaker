# SlideSpeaker API Makefile

# Variables
PYTHON := uv run python
UVICORN := uv run python -m uvicorn
RUFF := uv run ruff
MYPY := uv run mypy
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
	@echo "make admin-purge - Remove legacy file-id states (maintenance)"
	@echo "make admin-set-type TID=<id> [TYPE=video|podcast|both] [VIDEO=0|1] [PODCAST=0|1] - Adjust a task's type flags"
	@echo "make lint        - Run ruff linter"
	@echo "make format      - Run ruff formatter"
	@echo "make typecheck   - Run mypy type checker"
	@echo "make check       - Run both linting and type checking"
	@echo "make clean       - Clean temporary files"

# Install dependencies
.PHONY: install
install:
	uv sync --extra=dev

.PHONY: install_dev
install_dev:
	uv sync --extra=dev --extra=oss --extra=aws


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

# Admin maintenance
.PHONY: admin-purge
admin-purge: install
	$(PYTHON) -m api.scripts.ss_admin purge-legacy-file-states

.PHONY: admin-set-type
admin-set-type: install
	@if [ -z "$(TID)" ]; then echo "Usage: make admin-set-type TID=<task_id> [TYPE=video|podcast|both] [VIDEO=0|1] [PODCAST=0|1]"; exit 1; fi; \
	FLAGS=""; \
	if [ -n "$(TYPE)" ]; then FLAGS="$$FLAGS --task-type $(TYPE)"; fi; \
	if [ -n "$(VIDEO)" ]; then if [ "$(VIDEO)" = "0" ] || [ "$(VIDEO)" = "false" ]; then FLAGS="$$FLAGS --no-generate-video"; else FLAGS="$$FLAGS --generate-video"; fi; fi; \
	if [ -n "$(PODCAST)" ]; then if [ "$(PODCAST)" = "0" ] || [ "$(PODCAST)" = "false" ]; then FLAGS="$$FLAGS --no-generate-podcast"; else FLAGS="$$FLAGS --generate-podcast"; fi; fi; \
	$(PYTHON) -m api.scripts.ss_admin set-type --task-id $(TID) $$FLAGS

# Linting with ruff
.PHONY: lint
lint: install
	$(RUFF) check .

# Formatting with ruff
.PHONY: format
format: install
	$(RUFF) format .

# Type checking with mypy
.PHONY: typecheck
typecheck: install
	$(MYPY) .

# Combined check (linting and type checking)
.PHONY: check
check: lint typecheck

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
