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
	@echo "make lint        - Run ruff linter"
	@echo "make format      - Run ruff formatter"
	@echo "make typecheck   - Run mypy type checker"
	@echo "make check       - Run both linting and type checking"
	@echo "make clean       - Clean temporary files"

# Install dependencies
.PHONY: install
install:
	uv sync --extra=dev

# Development server
.PHONY: dev
dev: install
	$(UVICORN) server:app --host 0.0.0.0 --port 8000 --reload

# Production server
.PHONY: start
start: install
	$(UVICORN) server:app --host 0.0.0.0 --port 8000

# Master worker (automatically spawns/manages multiple worker processes)
.PHONY: master-worker
master-worker: install
	$(PYTHON) master_worker.py

# CLI tool
.PHONY: cli
cli: install
	$(PYTHON) cli.py --help

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