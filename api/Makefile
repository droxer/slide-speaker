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
	@echo "make test        - Run tests"
	@echo "make lint        - Run code linting"
	@echo "make format      - Format code"
	@echo "make clean       - Clean temporary files"
	@echo "make redis-start - Start Redis server (macOS)"
	@echo "make redis-stop  - Stop Redis server (macOS)"
	@echo "make setup       - Initial setup (install deps + start redis)"

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

# Run tests
.PHONY: test
test:
	@echo "Running tests..."
	$(PYTHON) -m pytest tests/ -v

# Code linting
.PHONY: lint
lint:
	@echo "Running code linting..."
	$(PYTHON) -m ruff check .

# Format code
.PHONY: format
format:
	@echo "Formatting code..."
	$(PYTHON) -m ruff format .

# Clean temporary files
.PHONY: clean
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	rm -rf .ruff_cache
	rm -rf uploads/*.pdf uploads/*.pptx uploads/*.ppt
	rm -rf output/*.mp4 output/*.mp3 output/*.png

# Start Redis (macOS with Homebrew)
.PHONY: redis-start
redis-start:
	@echo "Starting Redis server..."
	brew services start redis

# Stop Redis (macOS with Homebrew)
.PHONY: redis-stop
redis-stop:
	@echo "Stopping Redis server..."
	brew services stop redis

# Initial setup
.PHONY: setup
setup: install redis-start
	@echo "Setup complete! Starting development server..."
	$(MAKE) dev

# Show current status
.PHONY: status
status:
	@echo "Checking Redis status..."
	brew services list | grep redis
	@echo "Checking Python version..."
	$(PYTHON) --version
	@echo "Checking installed packages..."
	uv pip list

.DEFAULT_GOAL := help