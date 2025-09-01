# SlideSpeaker Web Makefile

# Variables
NPM := npm
PNPM := pnpm

# Default target
.PHONY: help
help:
	@echo "SlideSpeaker Web - Makefile Commands"
	@echo "================================"
	@echo "make install     - Install dependencies (uses pnpm if available, falls back to npm)"
	@echo "make dev         - Start development server"
	@echo "make build       - Build production version"
	@echo "make start       - Start production server (serve build)"
	@echo "make test        - Run tests"
	@echo "make lint        - Run code linting"
	@echo "make format      - Format code"
	@echo "make clean       - Clean temporary files"
	@echo "make setup       - Initial setup (install deps)"
	@echo "make deploy      - Build and prepare for deployment"

# Install dependencies
.PHONY: install
install:
	@if command -v pnpm >/dev/null 2>&1; then \
		echo "Using pnpm to install dependencies..."; \
		pnpm install; \
	else \
		echo "Using npm to install dependencies..."; \
		npm install; \
	fi

# Development server
.PHONY: dev
dev:
	@if command -v pnpm >/dev/null 2>&1; then \
		pnpm start; \
	else \
		npm start; \
	fi

# Build production version
.PHONY: build
build:
	@if command -v pnpm >/dev/null 2>&1; then \
		pnpm build; \
	else \
		npm run build; \
	fi

# Start production server
.PHONY: start
start:
	npm install -g serve
	serve -s build

# Run tests
.PHONY: test
test:
	@if command -v pnpm >/dev/null 2>&1; then \
		pnpm test; \
	else \
		npm test; \
	fi

# Code linting
.PHONY: lint
lint:
	@if command -v pnpm >/dev/null 2>&1; then \
		pnpm run lint; \
	else \
		npm run lint; \
	fi

# Format code
.PHONY: format
format:
	@if command -v pnpm >/dev/null 2>&1; then \
		pnpm run format; \
	else \
		npm run format; \
	fi

# Clean temporary files
.PHONY: clean
clean:
	rm -rf node_modules
	rm -rf build
	rm -rf .cache

# Initial setup
.PHONY: setup
setup: install
	@echo "Setup complete! Starting development server..."
	$(MAKE) dev

# Deploy preparation
.PHONY: deploy
deploy: build
	@echo "Build complete. Ready for deployment."

.DEFAULT_GOAL := help