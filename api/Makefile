# SlideSpeaker API Makefile

# Variables
PYTHON := uv run python
UVICORN := uv run python -m uvicorn
PYTHON_VERSION := 3.12

# Default target
.PHONY: help
help:
	@echo "SlideSpeaker API - Makefile Commands"
	@echo "=================================="
	@echo "make install     - Install dependencies"
	@echo "make dev         - Start development server with auto-reload"
	@echo "make start       - Start production server"
	@echo "make clean       - Clean temporary files"

# Install dependencies
.PHONY: install
install:
	uv sync

# Development server
.PHONY: dev
dev: install
	$(UVICORN) main:app --host 0.0.0.0 --port 8000 --reload

# Production server
.PHONY: start
start: install
	$(UVICORN) main:app --host 0.0.0.0 --port 8000

# Clean temporary files
.PHONY: clean
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	rm -rf .ruff_cache
	rm -rf uploads/*.pdf uploads/*.pptx uploads/*.ppt
	rm -rf output/*.mp4 output/*.mp3 output/*.png


.DEFAULT_GOAL := help